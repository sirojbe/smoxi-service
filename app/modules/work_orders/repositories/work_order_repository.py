"""Work order repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.models.work_order import WorkOrder, WorkOrderStatusHistory
from app.repositories.base import BaseRepository

# Hidden from the operational board unless explicitly filtered.
COMPLETED_BOARD_STATUSES: frozenset[str] = frozenset(
    {
        WorkOrderStatus.DELIVERED.value,
        WorkOrderStatus.CLOSED.value,
        WorkOrderStatus.ARCHIVED.value,
        WorkOrderStatus.CANCELLED.value,
    }
)


class WorkOrderRepository(BaseRepository[WorkOrder]):
    """Persistence for work orders."""

    model = WorkOrder

    def get_with_history(self, work_order_id: int) -> WorkOrder | None:
        """Return work order with status history."""
        stmt = (
            select(WorkOrder)
            .where(WorkOrder.id == work_order_id, WorkOrder.deleted_at.is_(None))
            .options(
                selectinload(WorkOrder.status_history),
                selectinload(WorkOrder.parts),
            )
        )
        return self._session.scalar(stmt)

    def search(
        self,
        company_id: int,
        *,
        query: str | None = None,
        status: str | None = None,
        branch_id: int | None = None,
        limit: int = 300,
        include_completed: bool = False,
    ) -> list[WorkOrder]:
        """Search work orders for a company (optional branch filter).

        By default completed orders (delivered/closed/…) are excluded so the
        board stays operational; pick a specific status or search by number
        to find them again.
        """
        stmt = (
            self._base_query()
            .where(WorkOrder.company_id == company_id)
            .order_by(WorkOrder.received_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        elif not include_completed and not (query and query.strip()):
            stmt = stmt.where(WorkOrder.status.notin_(COMPLETED_BOARD_STATUSES))
        if branch_id is not None:
            stmt = stmt.where(
                or_(
                    WorkOrder.branch_id == branch_id,
                    WorkOrder.branch_id.is_(None),
                )
            )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    WorkOrder.number.ilike(pattern),
                    WorkOrder.problem_description.ilike(pattern),
                )
            )
        return list(self._session.scalars(stmt))

    def count_today(self, company_id: int, *, day_start: datetime) -> int:
        """Count work orders received since *day_start*."""
        stmt = (
            select(func.count())
            .select_from(WorkOrder)
            .where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.received_at >= day_start,
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def next_sequence(self, company_id: int, prefix: str | None = None) -> int:
        """
        Return next company-wide sequence for work order numbers.

        Includes soft-deleted rows so numbers never reuse. When *prefix* is
        given (legacy), counts only numbers with that prefix.
        """
        stmt = select(func.count()).select_from(WorkOrder).where(
            WorkOrder.company_id == company_id,
        )
        if prefix:
            stmt = stmt.where(WorkOrder.number.like(f"{prefix}%"))
        return int(self._session.scalar(stmt) or 0) + 1

    def add_status_history(self, entry: WorkOrderStatusHistory) -> WorkOrderStatusHistory:
        """Persist a status history row."""
        self._session.add(entry)
        self._session.flush()
        return entry

    def list_for_customer(self, customer_id: int, *, limit: int = 20) -> list[WorkOrder]:
        """Return recent work orders for a customer."""
        stmt = (
            self._base_query()
            .where(WorkOrder.customer_id == customer_id)
            .order_by(WorkOrder.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
