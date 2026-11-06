"""Device ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.customers.models.customer import Customer

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Device(AuditMixin, Base):
    """Customer device registered for service history."""

    __tablename__ = "devices"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    device_type: Mapped[str] = mapped_column(String(64), nullable=False, default="phone")
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(150), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    imei: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="devices")

    @property
    def display_label(self) -> str:
        """Human-readable device label for lists."""
        parts = [p for p in (self.brand, self.model) if p]
        label = " ".join(parts) if parts else self.model
        if self.imei:
            return f"{label} ({self.imei})"
        if self.serial_number:
            return f"{label} ({self.serial_number})"
        return label
