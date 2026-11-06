"""Customer repository."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.phone import digits_only, phone_lookup_variants
from app.modules.customers.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Persistence for customers."""

    model = Customer

    def get_by_phone(
        self,
        company_id: int,
        phone: str,
        *,
        include_deleted: bool = False,
    ) -> Customer | None:
        """Return customer by company and phone (exact, then normalized variants)."""
        for candidate in phone_lookup_variants(phone):
            stmt = self._base_query(include_deleted=include_deleted).where(
                Customer.company_id == company_id,
                Customer.phone == candidate,
            )
            found = self._session.scalar(stmt)
            if found is not None:
                return found

        target = digits_only(phone)
        if len(target) < 9:
            return None
        rows = list(
            self._session.scalars(
                self._base_query(include_deleted=include_deleted).where(
                    Customer.company_id == company_id
                )
            )
        )
        for row in rows:
            row_digits = digits_only(row.phone)
            if row_digits == target or row_digits.endswith(target[-9:]):
                return row
        return None

    def get_by_telegram_chat_id(self, company_id: int, chat_id: str) -> Customer | None:
        stmt = self._base_query().where(
            Customer.company_id == company_id,
            Customer.telegram_chat_id == str(chat_id),
        )
        return self._session.scalar(stmt)

    def search(
        self,
        company_id: int,
        *,
        query: str | None = None,
        limit: int = 200,
    ) -> list[Customer]:
        """Search customers by name, phone, or email."""
        stmt = (
            self._base_query()
            .where(Customer.company_id == company_id)
            .options(selectinload(Customer.devices))
            .order_by(Customer.display_name)
            .limit(limit)
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Customer.display_name.ilike(pattern),
                    Customer.phone.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )
        return list(self._session.scalars(stmt).unique())

    def get_with_devices(self, customer_id: int) -> Customer | None:
        """Return customer with devices loaded."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id, Customer.deleted_at.is_(None))
            .options(selectinload(Customer.devices))
        )
        return self._session.scalar(stmt)
