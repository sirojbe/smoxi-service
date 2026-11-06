"""Calendar application service."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.time import utc_now
from app.modules.calendar.models.event import CalendarEvent
from app.modules.calendar.repositories.event_repository import CalendarEventRepository
from app.modules.calendar.schemas.event_schema import (
    CalendarEventCreateSchema,
    CalendarEventUpdateSchema,
)
from app.services.audit_service import AuditService


class CalendarService:
    """Create, update, list, and soft-delete calendar events."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._events = CalendarEventRepository(session)
        self._audit = AuditService(session)

    def list_range(
        self,
        company_id: int,
        *,
        range_start: datetime,
        range_end: datetime,
        technician_id: int | None = None,
        event_type: str | None = None,
    ) -> list[CalendarEvent]:
        if range_end <= range_start:
            raise ValidationError("Sana oraligʻi notoʻgʻri.")
        return self._events.list_in_range(
            company_id,
            range_start=range_start,
            range_end=range_end,
            technician_id=technician_id,
            event_type=event_type,
        )

    def list_agenda(self, company_id: int, *, days: int = 30) -> list[CalendarEvent]:
        return self._events.list_agenda(
            company_id, from_at=utc_now() - timedelta(hours=1), limit=200
        )

    def get_event(self, event_id: int) -> CalendarEvent:
        return self._events.require_by_id(event_id)

    def create_event(
        self,
        company_id: int,
        payload: CalendarEventCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> CalendarEvent:
        self._validate_times(payload.starts_at, payload.ends_at)
        row = CalendarEvent(
            company_id=company_id,
            title=payload.title,
            description=payload.description,
            event_type=payload.event_type,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            all_day=payload.all_day,
            work_order_id=payload.work_order_id,
            technician_id=payload.technician_id,
            location=payload.location,
            color=payload.color,
            reminder_minutes=payload.reminder_minutes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._events.add(row)
        self._audit.record(
            "calendar_event_created",
            actor_id=actor_id,
            entity_type="CalendarEvent",
            entity_id=row.id,
            entity_uuid=row.uuid,
            message=row.title,
        )
        return row

    def update_event(
        self,
        event_id: int,
        payload: CalendarEventUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> CalendarEvent:
        row = self._events.require_by_id(event_id)
        self._validate_times(payload.starts_at, payload.ends_at)
        row.title = payload.title
        row.description = payload.description
        row.event_type = payload.event_type
        row.starts_at = payload.starts_at
        row.ends_at = payload.ends_at
        row.all_day = payload.all_day
        row.work_order_id = payload.work_order_id
        row.technician_id = payload.technician_id
        row.location = payload.location
        row.color = payload.color
        row.reminder_minutes = payload.reminder_minutes
        row.updated_by = actor_id
        self._events.save(row)
        self._audit.record(
            "calendar_event_updated",
            actor_id=actor_id,
            entity_type="CalendarEvent",
            entity_id=row.id,
            entity_uuid=row.uuid,
            message=row.title,
        )
        return row

    def reschedule(
        self,
        event_id: int,
        *,
        starts_at: datetime,
        ends_at: datetime,
        actor_id: int | None = None,
    ) -> CalendarEvent:
        self._validate_times(starts_at, ends_at)
        row = self._events.require_by_id(event_id)
        row.starts_at = starts_at
        row.ends_at = ends_at
        row.updated_by = actor_id
        self._events.save(row)
        self._audit.record(
            "calendar_event_rescheduled",
            actor_id=actor_id,
            entity_type="CalendarEvent",
            entity_id=row.id,
            entity_uuid=row.uuid,
            message=f"{starts_at} → {ends_at}",
        )
        return row

    def soft_delete(self, event_id: int, *, actor_id: int | None = None) -> None:
        row = self._events.require_by_id(event_id)
        row.soft_delete(actor_id=actor_id)
        self._audit.record(
            "calendar_event_deleted",
            actor_id=actor_id,
            entity_type="CalendarEvent",
            entity_id=row.id,
            entity_uuid=row.uuid,
            message=row.title,
        )

    @staticmethod
    def _validate_times(starts_at: datetime, ends_at: datetime) -> None:
        if ends_at <= starts_at:
            raise ValidationError("Tugash vaqti boshlanishdan keyin boʻlishi kerak.")
        if starts_at.tzinfo is None or ends_at.tzinfo is None:
            raise ValidationError("Vaqt zonasi (UTC) majburiy.")
