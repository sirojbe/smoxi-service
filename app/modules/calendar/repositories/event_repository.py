"""Calendar event repository."""

from __future__ import annotations

from datetime import datetime

from app.modules.calendar.models.event import CalendarEvent
from app.repositories.base import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    """Persistence for calendar_events."""

    model = CalendarEvent

    def list_in_range(
        self,
        company_id: int,
        *,
        range_start: datetime,
        range_end: datetime,
        technician_id: int | None = None,
        event_type: str | None = None,
        limit: int = 500,
    ) -> list[CalendarEvent]:
        stmt = (
            self._base_query()
            .where(
                CalendarEvent.company_id == company_id,
                CalendarEvent.starts_at < range_end,
                CalendarEvent.ends_at > range_start,
            )
            .order_by(CalendarEvent.starts_at.asc())
            .limit(limit)
        )
        if technician_id is not None:
            stmt = stmt.where(CalendarEvent.technician_id == technician_id)
        if event_type:
            stmt = stmt.where(CalendarEvent.event_type == event_type)
        return list(self._session.scalars(stmt))

    def list_agenda(
        self,
        company_id: int,
        *,
        from_at: datetime,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        stmt = (
            self._base_query()
            .where(
                CalendarEvent.company_id == company_id,
                CalendarEvent.ends_at >= from_at,
            )
            .order_by(CalendarEvent.starts_at.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
