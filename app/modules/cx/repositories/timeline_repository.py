"""CX timeline repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cx.models import WorkOrderTimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[WorkOrderTimelineEvent]):
    """Persistence for work order timeline events."""

    model = WorkOrderTimelineEvent

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_work_order(
        self,
        work_order_id: int,
        *,
        customer_only: bool = False,
    ) -> list[WorkOrderTimelineEvent]:
        stmt = (
            self._base_query()
            .where(WorkOrderTimelineEvent.work_order_id == work_order_id)
            .order_by(WorkOrderTimelineEvent.created_at.desc(), WorkOrderTimelineEvent.id.desc())
        )
        if customer_only:
            from app.modules.cx.models.events import VISIBILITY_CUSTOMER

            stmt = stmt.where(WorkOrderTimelineEvent.visibility == VISIBILITY_CUSTOMER)
        return list(self._session.scalars(stmt))

    def count_for_work_order(self, work_order_id: int) -> int:
        stmt = select(WorkOrderTimelineEvent.id).where(
            WorkOrderTimelineEvent.work_order_id == work_order_id,
            WorkOrderTimelineEvent.deleted_at.is_(None),
        )
        return len(list(self._session.scalars(stmt)))
