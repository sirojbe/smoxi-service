"""Calendar event ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.models.base import AuditMixin, Base

EVENT_APPOINTMENT = "appointment"
EVENT_SHIFT = "shift"
EVENT_REMINDER = "reminder"
EVENT_WORK_ORDER = "work_order"

EVENT_TYPES = frozenset(
    {EVENT_APPOINTMENT, EVENT_SHIFT, EVENT_REMINDER, EVENT_WORK_ORDER}
)


class CalendarEvent(AuditMixin, Base):
    """Company calendar event (appointment, shift, reminder, WO link)."""

    __tablename__ = "calendar_events"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EVENT_APPOINTMENT
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_orders.id"), nullable=True, index=True
    )
    technician_id: Mapped[int | None] = mapped_column(
        ForeignKey("technicians.id"), nullable=True, index=True
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reminder_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
