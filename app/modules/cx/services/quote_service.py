"""Customer quote / approval helpers (CX-D)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.cx.models.events import (
    EVENT_ADMIN_OVERRIDE,
    EVENT_NOTE_ADDED,
    VISIBILITY_STAFF,
    default_visibility_for_event,
    event_label,
)
from app.modules.cx.models.timeline_event import WorkOrderTimelineEvent
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.models.work_order import WorkOrder, WorkOrderStatusHistory
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.schemas.work_order_schema import WorkOrderStatusChangeSchema
from app.services.audit_service import AuditService
from app.telegram.notifier import TelegramNotifier

# Statuses that count as "repair started" and require prior approval.
_REPAIR_STATUSES = frozenset({WorkOrderStatus.REPAIRING})


class QuoteService:
    """Submit quotes, check approval, and record admin overrides."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._customers = CustomerRepository(session)
        self._companies = CompanyRepository(session)
        self._audit = AuditService(session)

    def has_customer_approval(self, work_order_id: int) -> bool:
        """True if WO was ever in APPROVED (or is currently APPROVED)."""
        work_order = self._work_orders.require_by_id(work_order_id)
        if work_order.status == WorkOrderStatus.APPROVED.value:
            return True
        stmt = select(WorkOrderStatusHistory).where(
            WorkOrderStatusHistory.work_order_id == work_order_id,
            WorkOrderStatusHistory.to_status == WorkOrderStatus.APPROVED.value,
        )
        return self._session.scalar(stmt) is not None

    def assert_repair_allowed(
        self,
        work_order: WorkOrder,
        *,
        target: WorkOrderStatus,
        admin_override: bool = False,
        note: str | None = None,
        actor_id: int | None = None,
    ) -> None:
        """Block repair start without approval unless admin override + note."""
        if target not in _REPAIR_STATUSES:
            return
        if self.has_customer_approval(work_order.id):
            return
        if admin_override:
            reason = (note or "").strip()
            if not reason:
                raise ValidationError(
                    "Admin istisnosi uchun sabab (izoh) majburiy."
                )
            # Timeline is recorded by start_repair_with_override or caller.
            return
        raise ValidationError(
            "Taʼmir boshlash uchun mijoz roziligi kerak "
            "(yoki admin istisnosi + sabab)."
        )

    def record_admin_override(
        self,
        work_order_id: int,
        *,
        reason: str,
        actor_id: int | None = None,
    ) -> WorkOrderTimelineEvent:
        work_order = self._work_orders.require_by_id(work_order_id)
        code = EVENT_ADMIN_OVERRIDE
        event = WorkOrderTimelineEvent(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            event_code=code,
            visibility=default_visibility_for_event(code),
            title=event_label(code),
            notes=reason.strip(),
            actor_id=actor_id,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(event)
        self._session.flush()
        self._audit.record(
            "cx_admin_override",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=reason.strip()[:200],
        )
        return event

    def submit_quote(
        self,
        work_order_id: int,
        *,
        estimated_cost: int,
        actor_id: int | None = None,
        note: str | None = None,
    ) -> WorkOrder:
        """
        Update price and move to waiting_customer_approval (re-quote if needed).

        From DIAGNOSING / WAITING_PARTS / APPROVED (price change) paths.
        """
        if estimated_cost < 0:
            raise ValidationError("Smeta summasi manfiy boʻlishi mumkin emas.")
        work_order = self._work_orders.require_by_id(work_order_id)
        previous_cost = work_order.estimated_cost
        work_order.estimated_cost = estimated_cost
        work_order.updated_by = actor_id
        self._work_orders.save(work_order)

        self._session.add(
            WorkOrderTimelineEvent(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                event_code=EVENT_NOTE_ADDED,
                visibility=VISIBILITY_STAFF,
                title="Smeta yangilandi",
                notes=(
                    f"{previous_cost or 0} → {estimated_cost} soʻm"
                    + (f"; {note}" if note else "")
                ),
                actor_id=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

        from app.modules.work_orders.services.work_order_service import WorkOrderService

        wo_service = WorkOrderService(self._session)
        current = WorkOrderStatus(work_order.status)
        if current == WorkOrderStatus.RECEIVED:
            wo_service.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.DIAGNOSING.value,
                    note="Smeta — diagnostika",
                ),
                actor_id=actor_id,
                notify=False,
                auto_advance=False,
            )
            current = WorkOrderStatus.DIAGNOSING
        if current in {
            WorkOrderStatus.DIAGNOSING,
            WorkOrderStatus.WAITING_PARTS,
            WorkOrderStatus.APPROVED,
            WorkOrderStatus.REPAIRING,
        }:
            # Price change after approval → re-approval required.
            if current == WorkOrderStatus.REPAIRING:
                raise ValidationError(
                    "Taʼmir davomida smeta oʻzgartirilmaydi — "
                    "avval diagnostikaga qayting."
                )
            if current != WorkOrderStatus.WAITING_CUSTOMER_APPROVAL:
                # WAITING_PARTS / APPROVED → need path via WAITING_CUSTOMER_APPROVAL
                if current == WorkOrderStatus.WAITING_PARTS:
                    wo_service.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
                            note=note or "Qayta smeta — rozilik",
                        ),
                        actor_id=actor_id,
                        notify=False,
                        auto_advance=False,
                    )
                elif current == WorkOrderStatus.APPROVED:
                    # No direct APPROVED → WAITING_CUSTOMER_APPROVAL; use parts detour
                    # or stay and notify — BA allows waiting_parts ↔ approval.
                    # Force via waiting_parts then approval if needed.
                    wo_service.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.WAITING_PARTS.value,
                            note="Qayta smeta uchun",
                        ),
                        actor_id=actor_id,
                        notify=False,
                        auto_advance=False,
                    )
                    wo_service.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
                            note=note or "Qayta smeta — rozilik",
                        ),
                        actor_id=actor_id,
                        notify=False,
                        auto_advance=False,
                    )
                elif current == WorkOrderStatus.DIAGNOSING:
                    wo_service.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
                            note=note or "Smeta tasdiqi",
                        ),
                        actor_id=actor_id,
                        notify=False,
                        auto_advance=False,
                    )
        elif current == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL:
            pass
        else:
            raise ValidationError(
                f"Hozirgi statusdan smeta yuborib boʻlmaydi: {work_order.status}."
            )

        work_order = self._work_orders.require_by_id(work_order_id)
        customer = self._customers.get_by_id(work_order.customer_id)
        company = self._companies.get_by_id(work_order.company_id)
        if customer is not None and company is not None:
            TelegramNotifier(self._session).notify_quote(work_order, customer, company)

        self._audit.record(
            "cx_quote_submitted",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=str(estimated_cost),
        )
        return work_order

    def start_repair_with_override(
        self,
        work_order_id: int,
        *,
        reason: str,
        actor_id: int | None = None,
    ) -> WorkOrder:
        """Bypass approval and move toward repairing (CX-D admin override)."""
        reason_clean = (reason or "").strip()
        if not reason_clean:
            raise ValidationError("Admin istisnosi uchun sabab majburiy.")

        self.record_admin_override(work_order_id, reason=reason_clean, actor_id=actor_id)

        from app.modules.work_orders.services.work_order_service import WorkOrderService

        wo_service = WorkOrderService(self._session)
        work_order = self._work_orders.require_by_id(work_order_id)
        current = WorkOrderStatus(work_order.status)

        if current == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL:
            wo_service.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.APPROVED.value,
                    note=f"Admin istisnosi: {reason_clean}",
                    admin_override=True,
                ),
                actor_id=actor_id,
                notify=False,
                auto_advance=False,
            )
            return wo_service.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.REPAIRING.value,
                    note=f"Admin istisnosi: {reason_clean}",
                    admin_override=True,
                ),
                actor_id=actor_id,
                notify=True,
                auto_advance=False,
            )

        if current == WorkOrderStatus.WAITING_PARTS:
            return wo_service.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.REPAIRING.value,
                    note=f"Admin istisnosi: {reason_clean}",
                    admin_override=True,
                ),
                actor_id=actor_id,
                notify=True,
                auto_advance=False,
            )

        if current == WorkOrderStatus.APPROVED:
            return wo_service.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.REPAIRING.value,
                    note=reason_clean,
                ),
                actor_id=actor_id,
                notify=True,
                auto_advance=False,
            )

        raise ValidationError(
            "Admin istisnosi faqat rozilik kutish / qism kutish / tasdiqlangan "
            "statuslardan mumkin."
        )
