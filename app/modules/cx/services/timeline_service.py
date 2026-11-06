"""CX timeline application service (append-only)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.modules.cx.models import WorkOrderTimelineEvent
from app.modules.cx.models.events import (
    default_visibility_for_event,
    event_for_status,
    event_label,
)
from app.modules.cx.repositories.timeline_repository import TimelineRepository
from app.modules.work_orders.models.work_order import WorkOrder
from app.services.audit_service import AuditService


@dataclass(frozen=True, slots=True)
class TimelineEventView:
    """UI-facing timeline row."""

    id: int
    event_code: str
    title: str
    notes: str | None
    visibility: str
    from_status: str | None
    to_status: str | None
    actor_id: int | None
    created_at: object


class TimelineService:
    """Record and list CX timeline events. Deletion is not allowed."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TimelineRepository(session)
        self._audit = AuditService(session)

    def list_events(
        self,
        work_order_id: int,
        *,
        customer_only: bool = False,
    ) -> list[TimelineEventView]:
        rows = self._repo.list_for_work_order(
            work_order_id, customer_only=customer_only
        )
        return [
            TimelineEventView(
                id=row.id,
                event_code=row.event_code,
                title=row.title,
                notes=row.notes,
                visibility=row.visibility,
                from_status=row.from_status,
                to_status=row.to_status,
                actor_id=row.actor_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def record_status_change(
        self,
        work_order: WorkOrder,
        *,
        from_status: str | None,
        to_status: str,
        actor_id: int | None,
        notes: str | None = None,
    ) -> WorkOrderTimelineEvent:
        """Append a timeline event for a status transition."""
        code = event_for_status(to_status)
        event = WorkOrderTimelineEvent(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            event_code=code,
            visibility=default_visibility_for_event(code),
            title=event_label(code),
            notes=notes,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._repo.add(event)
        self._session.flush()
        self._audit.record(
            "cx_timeline_event",
            actor_id=actor_id,
            entity_type="WorkOrderTimelineEvent",
            entity_id=event.id,
            entity_uuid=event.uuid,
            message=f"{work_order.number}:{code}",
        )
        return event

    def ensure_seeded_from_status_history(self, work_order: WorkOrder) -> int:
        """
        Backfill timeline from legacy status_history when empty.

        Returns number of events created.
        """
        if self._repo.count_for_work_order(work_order.id) > 0:
            return 0
        history = list(work_order.status_history or [])
        if not history:
            return 0
        created = 0
        for entry in sorted(history, key=lambda h: (h.changed_at, h.id)):
            self.record_status_change(
                work_order,
                from_status=entry.from_status,
                to_status=entry.to_status,
                actor_id=entry.changed_by,
                notes=entry.note,
            )
            created += 1
        return created

    def soft_delete_forbidden(self, *_args: object, **_kwargs: object) -> None:
        raise ValidationError("Timeline voqealarini oʻchirish taqiqlangan.")
