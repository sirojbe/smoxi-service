"""Customer ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.customers.models.device import Device

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Customer(AuditMixin, Base):
    """Service customer (individual or business)."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("company_id", "phone", name="uq_customers_company_phone"),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    business_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_clients.id"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="individual")
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    devices: Mapped[list[Device]] = relationship(
        "Device",
        back_populates="customer",
    )
