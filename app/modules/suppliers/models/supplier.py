"""Supplier and purchase order ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base
from app.modules.suppliers.models.enums import PurchaseOrderStatus


class Supplier(AuditMixin, Base):
    """Parts / goods supplier."""

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_suppliers_company_code"),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    purchase_orders: Mapped[list[PurchaseOrder]] = relationship(
        "PurchaseOrder",
        back_populates="supplier",
    )


class PurchaseOrder(AuditMixin, Base):
    """Purchase order to a supplier."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_purchase_orders_company_number"),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    supplier: Mapped[Supplier] = relationship("Supplier", back_populates="purchase_orders")
    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        "PurchaseOrderLine",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )


class PurchaseOrderLine(Base):
    """Line on a purchase order."""

    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_items.id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    purchase_order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")
