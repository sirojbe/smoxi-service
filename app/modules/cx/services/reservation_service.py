"""Part reservation and stock deduction (CX-F)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.modules.cx.models.cx_entities import PartReservation
from app.modules.cx.models.events import EVENT_NOTE_ADDED, VISIBILITY_STAFF
from app.modules.cx.models.timeline_event import WorkOrderTimelineEvent
from app.modules.inventory.schemas.item_schema import StockAdjustSchema
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.work_orders.models.work_order import WorkOrder
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService


class ReservationService:
    """Reserve parts on approval; consume stock when repair completes."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._inventory = InventoryService(session)
        self._audit = AuditService(session)

    def reserve_for_work_order(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> list[PartReservation]:
        work_order = self._work_orders.require_by_id(work_order_id)
        created: list[PartReservation] = []
        for part in work_order.parts or []:
            if part.inventory_item_id is None:
                continue
            item = self._inventory.get_item(part.inventory_item_id)
            available = item.quantity_on_hand - self._reserved_qty(item.id, exclude_wo=work_order.id)
            if available < part.quantity:
                raise ValidationError(
                    f"Zaxira yetarli emas: {item.name} "
                    f"(kerak {part.quantity}, mavjud {available})."
                )
            existing = self._get_open(work_order.id, part.inventory_item_id)
            if existing is not None:
                existing.quantity = part.quantity
                existing.status = "reserved"
                existing.updated_by = actor_id
                created.append(existing)
                continue
            row = PartReservation(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                inventory_item_id=part.inventory_item_id,
                quantity=part.quantity,
                status="reserved",
                created_by=actor_id,
                updated_by=actor_id,
            )
            self._session.add(row)
            created.append(row)
        self._session.flush()
        if created:
            self._note(
                work_order,
                f"Qismlar rezerv qilindi ({len(created)})",
                actor_id,
            )
        return created

    def consume_for_work_order(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> int:
        """Deduct reserved stock; return number of lines consumed."""
        work_order = self._work_orders.require_by_id(work_order_id)
        stmt = select(PartReservation).where(
            PartReservation.work_order_id == work_order_id,
            PartReservation.status == "reserved",
            PartReservation.deleted_at.is_(None),
        )
        rows = list(self._session.scalars(stmt))
        count = 0
        for row in rows:
            self._inventory.adjust_stock(
                row.inventory_item_id,
                StockAdjustSchema(
                    movement_type="out",
                    quantity=row.quantity,
                    reason=f"WO {work_order.number} taʼmir",
                    reference=work_order.number,
                ),
                actor_id=actor_id,
            )
            row.status = "consumed"
            row.updated_by = actor_id
            count += 1
        if count:
            self._note(work_order, f"Qismlar yozib chiqarildi ({count})", actor_id)
            self._audit.record(
                "cx_parts_consumed",
                actor_id=actor_id,
                entity_type="WorkOrder",
                entity_id=work_order.id,
                entity_uuid=work_order.uuid,
                message=str(count),
            )
        return count

    def _reserved_qty(self, item_id: int, *, exclude_wo: int) -> int:
        stmt = select(PartReservation).where(
            PartReservation.inventory_item_id == item_id,
            PartReservation.status == "reserved",
            PartReservation.deleted_at.is_(None),
            PartReservation.work_order_id != exclude_wo,
        )
        return sum(r.quantity for r in self._session.scalars(stmt))

    def _get_open(self, work_order_id: int, item_id: int) -> PartReservation | None:
        stmt = select(PartReservation).where(
            PartReservation.work_order_id == work_order_id,
            PartReservation.inventory_item_id == item_id,
            PartReservation.deleted_at.is_(None),
        )
        return self._session.scalar(stmt)

    def _note(self, work_order: WorkOrder, title: str, actor_id: int | None) -> None:
        self._session.add(
            WorkOrderTimelineEvent(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                event_code=EVENT_NOTE_ADDED,
                visibility=VISIBILITY_STAFF,
                title=title,
                actor_id=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
