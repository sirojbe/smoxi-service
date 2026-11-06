"""License activation model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class LicenseRecord(AuditMixin, Base):
    """Per-tenant software license state."""

    __tablename__ = "licenses"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False, default="trial")
    license_key_masked: Mapped[str] = mapped_column(String(64), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="trial")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
