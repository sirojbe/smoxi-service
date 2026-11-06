"""Inventory item and movement repositories."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.modules.inventory.models.item import InventoryItem, StockMovement
from app.repositories.base import BaseRepository


class InventoryItemRepository(BaseRepository[InventoryItem]):
    """Persistence for inventory items."""

    model = InventoryItem

    def get_by_sku(self, company_id: int, sku: str) -> InventoryItem | None:
        """Return first item by SKU (any warehouse)."""
        stmt = self._base_query().where(
            InventoryItem.company_id == company_id,
            InventoryItem.sku == sku,
        )
        return self._session.scalar(stmt)

    def get_by_sku_warehouse(
        self,
        company_id: int,
        sku: str,
        warehouse_id: int,
    ) -> InventoryItem | None:
        """Return item by SKU within a warehouse."""
        stmt = self._base_query().where(
            InventoryItem.company_id == company_id,
            InventoryItem.sku == sku,
            InventoryItem.warehouse_id == warehouse_id,
        )
        return self._session.scalar(stmt)

    def search(
        self,
        company_id: int,
        *,
        query: str | None = None,
        low_stock_only: bool = False,
        limit: int = 1000,
    ) -> list[InventoryItem]:
        """Search inventory items."""
        stmt = (
            self._base_query()
            .where(InventoryItem.company_id == company_id)
            .options(selectinload(InventoryItem.warehouse))
            .order_by(InventoryItem.name)
            .limit(limit)
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    InventoryItem.name.ilike(pattern),
                    InventoryItem.sku.ilike(pattern),
                    InventoryItem.barcode.ilike(pattern),
                    InventoryItem.category.ilike(pattern),
                )
            )
        items = list(self._session.scalars(stmt).unique())
        if low_stock_only:
            items = [item for item in items if item.is_low_stock]
        return items

    def list_movements(self, item_id: int, *, limit: int = 100) -> list[StockMovement]:
        """Return recent movements for an item."""
        stmt = (
            select(StockMovement)
            .where(StockMovement.item_id == item_id)
            .order_by(StockMovement.moved_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def add_movement(self, movement: StockMovement) -> StockMovement:
        """Persist a stock movement."""
        self._session.add(movement)
        self._session.flush()
        return movement
