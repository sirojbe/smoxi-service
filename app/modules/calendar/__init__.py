"""Calendar module — scheduling, appointments, reminders."""

from app.modules.calendar.models.event import CalendarEvent
from app.modules.calendar.services.calendar_service import CalendarService

__all__ = ["CalendarEvent", "CalendarService"]
