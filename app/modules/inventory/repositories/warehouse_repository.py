"""Warehouse repository."""

from __future__ import annotations

from app.modules.inventory.models.warehouse import Warehouse
from app.repositories.base import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    """Persistence for warehouses."""

    model = Warehouse

    def get_default(self, company_id: int) -> Warehouse | None:
        """Return the default warehouse for a company."""
        stmt = (
            self._base_query()
            .where(
                Warehouse.company_id == company_id,
                Warehouse.is_default.is_(True),
                Warehouse.is_active.is_(True),
            )
        )
        return self._session.scalar(stmt)

    def get_by_code(self, company_id: int, code: str) -> Warehouse | None:
        """Return warehouse by code."""
        stmt = self._base_query().where(
            Warehouse.company_id == company_id,
            Warehouse.code == code,
        )
        return self._session.scalar(stmt)

    def list_active(self, company_id: int) -> list[Warehouse]:
        """Return active warehouses."""
        stmt = (
            self._base_query()
            .where(Warehouse.company_id == company_id, Warehouse.is_active.is_(True))
            .order_by(Warehouse.name)
        )
        return list(self._session.scalars(stmt))
