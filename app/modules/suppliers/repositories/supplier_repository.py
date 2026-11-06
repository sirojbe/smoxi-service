"""Supplier and purchase order repositories."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.modules.suppliers.models.supplier import PurchaseOrder, Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    """Persistence for suppliers."""

    model = Supplier

    def get_by_code(self, company_id: int, code: str) -> Supplier | None:
        stmt = self._base_query().where(
            Supplier.company_id == company_id,
            Supplier.code == code,
        )
        return self._session.scalar(stmt)

    def search(self, company_id: int, *, query: str | None = None) -> list[Supplier]:
        stmt = (
            self._base_query()
            .where(Supplier.company_id == company_id)
            .order_by(Supplier.name)
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Supplier.name.ilike(pattern),
                    Supplier.code.ilike(pattern),
                    Supplier.phone.ilike(pattern),
                )
            )
        return list(self._session.scalars(stmt))


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    """Persistence for purchase orders."""

    model = PurchaseOrder

    def get_with_lines(self, purchase_order_id: int) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == purchase_order_id, PurchaseOrder.deleted_at.is_(None))
            .options(
                selectinload(PurchaseOrder.lines),
                selectinload(PurchaseOrder.supplier),
            )
        )
        return self._session.scalar(stmt)

    def list_for_company(self, company_id: int, *, limit: int = 200) -> list[PurchaseOrder]:
        stmt = (
            self._base_query()
            .where(PurchaseOrder.company_id == company_id)
            .options(selectinload(PurchaseOrder.supplier), selectinload(PurchaseOrder.lines))
            .order_by(PurchaseOrder.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).unique())

    def next_sequence(self, company_id: int, prefix: str) -> int:
        stmt = (
            select(func.count())
            .select_from(PurchaseOrder)
            .where(
                PurchaseOrder.company_id == company_id,
                PurchaseOrder.number.like(f"{prefix}%"),
            )
        )
        return int(self._session.scalar(stmt) or 0) + 1
