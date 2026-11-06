"""Work order application service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.time import utc_now
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.customers.repositories.device_repository import DeviceRepository
from app.modules.cx.services.timeline_service import TimelineService
from app.modules.cx.services.wo_qr_service import WorkOrderQrService
from app.modules.work_orders.models.status import (
    WorkOrderStatus,
    assert_transition_allowed,
    next_statuses,
    status_label,
)
from app.modules.work_orders.models.work_order import (
    WorkOrder,
    WorkOrderPart,
    WorkOrderStatusHistory,
)
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.schemas.work_order_schema import (
    WorkOrderCreateSchema,
    WorkOrderStatusChangeSchema,
)
from app.services.audit_service import AuditService

# Operational shortcut path toward READY (shop floor).
_READY_CHAIN: tuple[WorkOrderStatus, ...] = (
    WorkOrderStatus.WAITING_PARTS,
    WorkOrderStatus.REPAIRING,
    WorkOrderStatus.TESTING,
    WorkOrderStatus.QUALITY_CHECK,
    WorkOrderStatus.READY,
)


@dataclass(frozen=True, slots=True)
class MarkReadyResult:
    """Result of marking a work order ready, including Telegram outcome."""

    work_order: WorkOrder
    telegram_sent: bool
    telegram_reason: str  # sent | no_token | no_chat | skipped | already_ready


@dataclass(frozen=True, slots=True)
class MarkDeliveredResult:
    """Result of handing the device to the customer (ready → delivered)."""

    work_order: WorkOrder
    telegram_sent: bool
    telegram_reason: str  # sent | no_token | no_chat | skipped | already_delivered
    unpaid_balance: int = 0


class WorkOrderService:
    """Use cases for reception intake and work order lifecycle."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._customers = CustomerRepository(session)
        self._devices = DeviceRepository(session)
        self._audit = AuditService(session)
        self._timeline = TimelineService(session)
        self._wo_qr = WorkOrderQrService(session)

    def list_work_orders(
        self,
        company_id: int,
        *,
        query: str | None = None,
        status: str | None = None,
        branch_id: int | None = None,
    ) -> list[WorkOrder]:
        """Return work orders for a company."""
        return self._work_orders.search(
            company_id,
            query=query,
            status=status,
            branch_id=branch_id,
        )

    def get_work_order(self, work_order_id: int) -> WorkOrder:
        """Return a work order with history."""
        work_order = self._work_orders.get_with_history(work_order_id)
        if work_order is None:
            raise NotFoundError("Ish buyurtmasi topilmadi.", entity="WorkOrder")
        return work_order

    def create_from_reception(
        self,
        company_id: int,
        payload: WorkOrderCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> WorkOrder:
        """Create a work order from the reception desk."""
        customer = self._customers.get_by_id(payload.customer_id)
        if customer is None or customer.company_id != company_id:
            raise NotFoundError("Mijoz topilmadi.", entity="Customer")
        if customer.is_blacklisted:
            raise ValidationError("Mijoz qora roʻyxatda. Yangi buyurtma ochib boʻlmaydi.")

        device_id = payload.device_id
        if device_id is not None:
            device = self._devices.get_by_id(device_id)
            if device is None or device.customer_id != customer.id:
                raise ValidationError("Qurilma tanlangan mijozga tegishli emas.")

        number = self._generate_number(company_id)
        parts_cost = 0
        parts_sale = 0
        for part in payload.parts:
            parts_cost += part.quantity * part.cost_price
            parts_sale += part.quantity * part.sale_price

        service_price = payload.estimated_cost if payload.estimated_cost is not None else 0
        # Customer total = labor/service + parts sale prices
        customer_total = service_price + parts_sale

        work_order = WorkOrder(
            company_id=company_id,
            branch_id=payload.branch_id,
            customer_id=customer.id,
            device_id=device_id,
            number=number,
            status=WorkOrderStatus.RECEIVED.value,
            priority=payload.priority,
            problem_description=payload.problem_description,
            work_scope=payload.work_scope,
            accessories=payload.accessories,
            notes=payload.notes,
            estimated_cost=customer_total,
            parts_cost_total=parts_cost,
            parts_sale_total=parts_sale,
            expense_total=parts_cost,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._work_orders.add(work_order)
        for part in payload.parts:
            line_cost = part.quantity * part.cost_price
            line_sale = part.quantity * part.sale_price
            work_order.parts.append(
                WorkOrderPart(
                    inventory_item_id=part.inventory_item_id,
                    name=part.name,
                    quantity=part.quantity,
                    cost_price=part.cost_price,
                    sale_price=part.sale_price,
                    line_cost=line_cost,
                    line_sale=line_sale,
                )
            )
        self._session.flush()
        self._wo_qr.ensure_public_token(work_order, actor_id=actor_id)
        self._work_orders.add_status_history(
            WorkOrderStatusHistory(
                work_order_id=work_order.id,
                from_status=None,
                to_status=WorkOrderStatus.RECEIVED.value,
                changed_by=actor_id,
                note="Qabulxonadan yaratildi",
            )
        )
        self._timeline.record_status_change(
            work_order,
            from_status=None,
            to_status=WorkOrderStatus.RECEIVED.value,
            actor_id=actor_id,
            notes="Qabulxonadan yaratildi",
        )
        self._audit.record(
            "work_order_created",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=f"{work_order.number}; xarajat={parts_cost}",
        )
        return work_order

    def change_status(
        self,
        work_order_id: int,
        payload: WorkOrderStatusChangeSchema,
        *,
        actor_id: int | None = None,
        notify: bool = True,
        auto_advance: bool = True,
    ) -> WorkOrder:
        """Transition a work order to a new status."""
        work_order = self.get_work_order(work_order_id)
        current, target = assert_transition_allowed(
            work_order.status,
            payload.to_status,
            note=payload.note,
        )
        # CX-D: repair requires customer approval or admin override + note
        from app.modules.cx.services.quote_service import QuoteService

        QuoteService(self._session).assert_repair_allowed(
            work_order,
            target=target,
            admin_override=bool(payload.admin_override),
            note=payload.note,
            actor_id=actor_id,
        )
        previous = work_order.status
        work_order.status = target.value
        work_order.updated_by = actor_id
        now = utc_now()
        if target == WorkOrderStatus.READY:
            work_order.ready_at = now
        if target == WorkOrderStatus.DELIVERED:
            work_order.delivered_at = now
        if target == WorkOrderStatus.CLOSED:
            work_order.closed_at = now

        self._work_orders.save(work_order)
        self._work_orders.add_status_history(
            WorkOrderStatusHistory(
                work_order_id=work_order.id,
                from_status=previous,
                to_status=target.value,
                changed_by=actor_id,
                note=payload.note,
            )
        )
        self._timeline.record_status_change(
            work_order,
            from_status=previous,
            to_status=target.value,
            actor_id=actor_id,
            notes=payload.note,
        )
        self._audit.record(
            "work_order_status_changed",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=f"{previous} -> {target.value}",
        )
        if notify:
            self._notify_status(work_order, target)

        if target == WorkOrderStatus.APPROVED:
            try:
                from app.modules.cx.services.reservation_service import ReservationService

                ReservationService(self._session).reserve_for_work_order(
                    work_order.id, actor_id=actor_id
                )
            except ValidationError:
                # Stock yetarli emas — waiting_parts ga o'tamiz
                if auto_advance:
                    return self.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.WAITING_PARTS.value,
                            note="Avtomatik: zaxira yetarli emas",
                        ),
                        actor_id=actor_id,
                        notify=notify,
                        auto_advance=False,
                    )
                raise

        if target == WorkOrderStatus.READY:
            from app.modules.cx.services.reservation_service import ReservationService

            ReservationService(self._session).consume_for_work_order(
                work_order.id, actor_id=actor_id
            )

        if target == WorkOrderStatus.DELIVERED:
            from app.modules.cx.services.warranty_service import WarrantyService

            WarrantyService(self._session).issue_for_delivery(
                work_order.id, actor_id=actor_id
            )

        # After customer approval → auto "waiting parts" or "repairing".
        if auto_advance and target == WorkOrderStatus.APPROVED:
            next_status = self.resolve_post_approval_status(work_order)
            return self.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=next_status.value,
                    note="Avtomatik: tasdiqdan keyin",
                ),
                actor_id=actor_id,
                notify=notify,
                auto_advance=False,
            )
        return work_order

    def resolve_post_approval_status(self, work_order: WorkOrder) -> WorkOrderStatus:
        """
        Choose next status after approval.

        - Parts missing / low stock → waiting_parts
        - Otherwise → repairing
        """
        from app.modules.inventory.repositories.item_repository import InventoryItemRepository

        parts = list(work_order.parts or [])
        if not parts:
            return WorkOrderStatus.REPAIRING

        items = InventoryItemRepository(self._session)
        for part in parts:
            if part.inventory_item_id is None:
                # Catalogga bogʻlanmagan qism — ehtiyot qism kutish.
                return WorkOrderStatus.WAITING_PARTS
            item = items.get_by_id(part.inventory_item_id)
            if item is None or item.quantity_on_hand < part.quantity:
                return WorkOrderStatus.WAITING_PARTS
        return WorkOrderStatus.REPAIRING

    def quick_set_status(
        self,
        work_order_id: int,
        to_status: str,
        *,
        actor_id: int | None = None,
        note: str | None = None,
    ) -> WorkOrder:
        """One-click status change used by UI shortcuts."""
        return self.change_status(
            work_order_id,
            WorkOrderStatusChangeSchema(to_status=to_status, note=note),
            actor_id=actor_id,
            notify=True,
            auto_advance=True,
        )

    def mark_ready(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> MarkReadyResult:
        """
        Advance the work order to READY via intermediate statuses, then notify.

        Intermediate steps skip Telegram; only the final READY notification is sent.
        """
        work_order = self.get_work_order(work_order_id)
        if work_order.status == WorkOrderStatus.READY.value:
            return MarkReadyResult(
                work_order=work_order,
                telegram_sent=False,
                telegram_reason="already_ready",
            )

        try:
            current = WorkOrderStatus(work_order.status)
        except ValueError as exc:
            raise ValidationError("Nomaʼlum status.") from exc

        if current not in _READY_CHAIN:
            raise ValidationError(
                f"«Tayyor» uchun mos emas: joriy status «{work_order.status}»."
            )

        start_index = _READY_CHAIN.index(current)
        steps = _READY_CHAIN[start_index + 1 :]
        if not steps:
            return MarkReadyResult(
                work_order=work_order,
                telegram_sent=False,
                telegram_reason="already_ready",
            )

        for step in steps[:-1]:
            work_order = self.change_status(
                work_order_id,
                WorkOrderStatusChangeSchema(
                    to_status=step.value,
                    note="Avtomatik: Tayyor",
                ),
                actor_id=actor_id,
                notify=False,
                auto_advance=False,
            )

        work_order = self.change_status(
            work_order_id,
            WorkOrderStatusChangeSchema(
                to_status=WorkOrderStatus.READY.value,
                note="Avtomatik: Tayyor",
            ),
            actor_id=actor_id,
            notify=False,
            auto_advance=False,
        )
        sent, reason = self._notify_ready_with_reason(work_order)
        try:
            from app.modules.notifications.services.notification_service import (
                NotificationService,
            )

            NotificationService(self._session).notify_work_order(
                work_order.company_id,
                title=f"Tayyor: {work_order.number}",
                body="Qurilma olib ketishga tayyor.",
                work_order_id=work_order.id,
                actor_id=actor_id,
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            from app.modules.automation.services.automation_service import (
                AutomationService,
            )

            AutomationService(self._session).fire_trigger(
                work_order.company_id,
                "wo_status",
                trigger_value="ready",
                context=work_order.number,
                actor_id=actor_id,
            )
        except Exception:  # noqa: BLE001
            pass
        return MarkReadyResult(
            work_order=work_order,
            telegram_sent=sent,
            telegram_reason=reason,
        )

    def unpaid_balance_for_work_order(self, work_order_id: int) -> int:
        """Sum of open invoice balances linked to this work order."""
        from sqlalchemy import select

        from app.modules.finance.models.enums import InvoiceStatus
        from app.modules.finance.models.invoice import Invoice

        work_order = self.get_work_order(work_order_id)
        stmt = select(Invoice).where(
            Invoice.work_order_id == work_order.id,
            Invoice.deleted_at.is_(None),
            Invoice.status.notin_(
                [InvoiceStatus.DRAFT.value, InvoiceStatus.VOID.value, InvoiceStatus.PAID.value]
            ),
        )
        total = 0
        for invoice in self._session.scalars(stmt):
            total += max(0, int(invoice.balance_due))
        return total

    def mark_delivered(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
        allow_unpaid: bool = False,
        note: str | None = None,
    ) -> MarkDeliveredResult:
        """
        Hand device to customer: READY (or REJECTED return) → DELIVERED.

        Issues warranty card via change_status and notifies Telegram.
        Unpaid invoices block delivery unless ``allow_unpaid`` is True (manager path).
        """
        work_order = self.get_work_order(work_order_id)
        if work_order.status == WorkOrderStatus.DELIVERED.value:
            return MarkDeliveredResult(
                work_order=work_order,
                telegram_sent=False,
                telegram_reason="already_delivered",
                unpaid_balance=0,
            )

        try:
            current = WorkOrderStatus(work_order.status)
        except ValueError as exc:
            raise ValidationError("Nomaʼlum status.") from exc

        if current not in {WorkOrderStatus.READY, WorkOrderStatus.REJECTED}:
            raise ValidationError(
                "Topshirish faqat «Tayyor» yoki «Rad etildi» statusidan mumkin. "
                f"Joriy: «{status_label(work_order.status)}»."
            )

        unpaid = self.unpaid_balance_for_work_order(work_order_id)
        if unpaid > 0 and not allow_unpaid:
            raise ValidationError(
                f"Toʻlov qoldigʻi {unpaid:,} soʻm. Avval toʻlang yoki qarz bilan "
                "topshirishni tasdiqlang.".replace(",", " ")
            )

        note_clean = (note or "").strip() or "Mijozga topshirildi"
        if unpaid > 0:
            note_clean = f"{note_clean} (qarz: {unpaid} soʻm)"

        work_order = self.change_status(
            work_order_id,
            WorkOrderStatusChangeSchema(
                to_status=WorkOrderStatus.DELIVERED.value,
                note=note_clean,
            ),
            actor_id=actor_id,
            notify=True,
            auto_advance=False,
        )

        sent, reason = self._notify_delivery_outcome(work_order)
        try:
            from app.modules.notifications.services.notification_service import (
                NotificationService,
            )

            NotificationService(self._session).notify_work_order(
                work_order.company_id,
                title=f"Topshirildi: {work_order.number}",
                body="Qurilma mijozga topshirildi.",
                work_order_id=work_order.id,
                actor_id=actor_id,
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            from app.modules.automation.services.automation_service import (
                AutomationService,
            )

            AutomationService(self._session).fire_trigger(
                work_order.company_id,
                "wo_status",
                trigger_value="delivered",
                context=work_order.number,
                actor_id=actor_id,
            )
        except Exception:  # noqa: BLE001
            pass
        return MarkDeliveredResult(
            work_order=work_order,
            telegram_sent=sent,
            telegram_reason=reason,
            unpaid_balance=unpaid,
        )

    def _notify_delivery_outcome(self, work_order: WorkOrder) -> tuple[bool, str]:
        """Telegram already sent in change_status; report whether customer can be reached."""
        from app.modules.companies.repositories.company_repository import CompanyRepository
        from app.security.secrets import company_bot_token

        customer = self._customers.get_by_id(work_order.customer_id)
        company = CompanyRepository(self._session).get_by_id(work_order.company_id)
        if customer is None or company is None:
            return False, "skipped"
        if not company_bot_token(company):
            return False, "no_token"
        if not (customer.telegram_chat_id or "").strip():
            return False, "no_chat"
        return True, "sent"

    def _notify_ready_with_reason(self, work_order: WorkOrder) -> tuple[bool, str]:
        from app.modules.companies.repositories.company_repository import CompanyRepository
        from app.telegram.notifier import TelegramNotifier

        customer = self._customers.get_by_id(work_order.customer_id)
        company = CompanyRepository(self._session).get_by_id(work_order.company_id)
        if customer is None or company is None:
            return False, "skipped"
        from app.security.secrets import company_bot_token

        if not company_bot_token(company):
            return False, "no_token"
        if not (customer.telegram_chat_id or "").strip():
            return False, "no_chat"
        sent = TelegramNotifier(self._session).notify_ready(work_order, customer, company)
        return (True, "sent") if sent else (False, "skipped")

    def _notify_status(self, work_order: WorkOrder, target: WorkOrderStatus) -> None:
        from app.modules.companies.repositories.company_repository import CompanyRepository
        from app.telegram.notifier import TelegramNotifier

        customer = self._customers.get_by_id(work_order.customer_id)
        company = CompanyRepository(self._session).get_by_id(work_order.company_id)
        if customer is None or company is None:
            return
        notifier = TelegramNotifier(self._session)
        if target == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL:
            notifier.notify_quote(work_order, customer, company)
        elif target == WorkOrderStatus.WAITING_PARTS:
            notifier.notify_waiting_parts(work_order, customer, company)
        elif target in {WorkOrderStatus.REPAIRING, WorkOrderStatus.TESTING}:
            notifier.notify_repairing(work_order, customer, company)
        elif target == WorkOrderStatus.READY:
            notifier.notify_ready(work_order, customer, company)
        elif target == WorkOrderStatus.DELIVERED:
            if hasattr(notifier, "notify_delivered"):
                notifier.notify_delivered(work_order, customer, company)
        elif target == WorkOrderStatus.WARRANTY:
            if hasattr(notifier, "notify_warranty"):
                notifier.notify_warranty(work_order, customer, company)

    def cancel_work_order(
        self,
        work_order_id: int,
        *,
        note: str,
        actor_id: int | None = None,
    ) -> WorkOrder:
        """Cancel a work order (requires note). Soft path — stays in history."""
        note_clean = (note or "").strip()
        if not note_clean:
            raise ValidationError("Bekor qilish uchun sabab (izoh) majburiy.")
        return self.change_status(
            work_order_id,
            WorkOrderStatusChangeSchema(
                to_status=WorkOrderStatus.CANCELLED.value,
                note=note_clean,
            ),
            actor_id=actor_id,
            notify=False,
            auto_advance=False,
        )

    def soft_delete_work_order(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> WorkOrder:
        """
        Soft-delete a work order (hide from lists). Prefer cancel first.

        Allowed for cancelled/rejected, or early intake mistakes
        (received / waiting approval) when staff confirms in UI.
        """
        work_order = self.get_work_order(work_order_id)
        removable = {
            WorkOrderStatus.CANCELLED.value,
            WorkOrderStatus.REJECTED.value,
            WorkOrderStatus.ARCHIVED.value,
            WorkOrderStatus.RECEIVED.value,
            WorkOrderStatus.WAITING_DIAGNOSIS.value,
            WorkOrderStatus.DIAGNOSING.value,
            WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
        }
        if work_order.status not in removable:
            raise ValidationError(
                "Avval buyurtmani «Bekor qilish» qiling, keyin roʻyxatdan oʻchiring."
            )
        self._work_orders.soft_delete(work_order, actor_id=actor_id)
        self._audit.record(
            "work_order_soft_deleted",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=work_order.number,
        )
        return work_order

    def available_transitions(self, work_order_id: int) -> list[WorkOrderStatus]:
        """Return allowed next statuses for a work order."""
        work_order = self.get_work_order(work_order_id)
        return next_statuses(work_order.status)

    def _generate_number(self, company_id: int) -> str:
        """Generate WO number: WO-000001 (company-wide sequential)."""
        seq = self._work_orders.next_sequence(company_id)
        return f"WO-{seq:06d}"
