"""Inventory item and stock movement ORM models."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.inventory.models.warehouse import Warehouse

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import AuditMixin, Base
from app.modules.inventory.models.enums import StockMovementType


class InventoryItem(AuditMixin, Base):
    """Spare part / inventory SKU."""

    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "warehouse_id",
            "sku",
            name="uq_inventory_items_company_wh_sku",
        ),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="dona")
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchase_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    warehouse: Mapped[Warehouse] = relationship("Warehouse")
    movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="item",
    )

    @property
    def is_low_stock(self) -> bool:
        """Return True when quantity is at or below minimum."""
        return self.quantity_on_hand <= self.min_quantity


class StockMovement(Base):
    """Immutable stock movement ledger entry."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_items.id"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=StockMovementType.ADJUST.value,
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="movements")
