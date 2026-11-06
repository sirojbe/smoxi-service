"""Calendar event Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.calendar.models.event import EVENT_APPOINTMENT, EVENT_TYPES


class CalendarEventCreateSchema(BaseModel):
    """Create calendar event payload."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    event_type: str = EVENT_APPOINTMENT
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    work_order_id: int | None = None
    technician_id: int | None = None
    location: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=16)
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Sarlavha majburiy.")
        return cleaned

    @field_validator("event_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError("Notoʻgʻri tadbir turi.")
        return value

    @field_validator("description", "location", "color", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class CalendarEventUpdateSchema(CalendarEventCreateSchema):
    """Update calendar event payload."""

    pass
