"""Finance ORM models: invoices, payments, cash sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import AuditMixin, Base
from app.modules.finance.models.enums import CashSessionStatus, InvoiceStatus, PaymentMethod


class CashSession(AuditMixin, Base):
    """Cash register open/close session."""

    __tablename__ = "cash_sessions"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    opened_by: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CashSessionStatus.OPEN.value,
        index=True,
    )
    opening_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closing_balance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_cash: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Invoice(AuditMixin, Base):
    """Customer invoice."""

    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("company_id", "number", name="uq_invoices_company_number"),)

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_orders.id"),
        nullable=True,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=InvoiceStatus.DRAFT.value,
        index=True,
    )
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    paid_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list[InvoiceLine]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="invoice")

    @property
    def balance_due(self) -> int:
        """Remaining amount to pay."""
        return max(self.total_amount - self.paid_amount, 0)


class InvoiceLine(Base):
    """Invoice line item."""

    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")


class Payment(AuditMixin, Base):
    """Payment allocated to an invoice."""

    __tablename__ = "payments"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id"),
        nullable=True,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentMethod.CASH.value,
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")
