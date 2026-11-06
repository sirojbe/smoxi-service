"""Automation rule ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.models.base import AuditMixin, Base

# Triggers
TRIGGER_WO_STATUS = "wo_status"
TRIGGER_LOW_STOCK = "low_stock"
TRIGGER_MANUAL = "manual"

# Actions
ACTION_NOTIFY = "notify"
ACTION_CALENDAR = "calendar_reminder"


class AutomationRule(AuditMixin, Base):
    """If-this-then-that style automation rule."""

    __tablename__ = "automation_rules"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trigger_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AutomationRun(AuditMixin, Base):
    """Immutable-ish run history for automation rules."""

    __tablename__ = "automation_runs"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("automation_rules.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
