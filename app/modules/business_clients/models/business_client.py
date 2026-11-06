"""B2B business client (UIUX §9.2 Companies) — not tenant Company."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class BusinessClient(AuditMixin, Base):
    """Corporate / B2B account linked to individual customers."""

    __tablename__ = "business_clients"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_business_clients_company_name"),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    credit_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    contacts: Mapped[list[BusinessClientContact]] = relationship(
        "BusinessClientContact",
        back_populates="business_client",
        cascade="all, delete-orphan",
    )


class BusinessClientContact(AuditMixin, Base):
    """Contact person for a B2B client."""

    __tablename__ = "business_client_contacts"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    business_client_id: Mapped[int] = mapped_column(
        ForeignKey("business_clients.id"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)

    business_client: Mapped[BusinessClient] = relationship(
        "BusinessClient",
        back_populates="contacts",
    )
