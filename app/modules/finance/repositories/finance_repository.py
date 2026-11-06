"""Finance repositories."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.modules.finance.models.enums import CashSessionStatus
from app.modules.finance.models.invoice import CashSession, Invoice, Payment
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Persistence for invoices."""

    model = Invoice

    def get_with_details(self, invoice_id: int) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
            )
        )
        return self._session.scalar(stmt)

    def search(
        self,
        company_id: int,
        *,
        query: str | None = None,
        status: str | None = None,
        limit: int = 300,
    ) -> list[Invoice]:
        stmt = (
            self._base_query()
            .where(Invoice.company_id == company_id)
            .options(selectinload(Invoice.lines), selectinload(Invoice.payments))
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Invoice.status == status)
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(or_(Invoice.number.ilike(pattern), Invoice.notes.ilike(pattern)))
        return list(self._session.scalars(stmt).unique())

    def next_sequence(self, company_id: int, prefix: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.company_id == company_id, Invoice.number.like(f"{prefix}%"))
        )
        return int(self._session.scalar(stmt) or 0) + 1

    def list_by_customer(self, customer_id: int, *, limit: int = 50) -> list[Invoice]:
        """Return recent invoices for a customer."""
        stmt = (
            self._base_query()
            .where(Invoice.customer_id == customer_id)
            .options(selectinload(Invoice.lines), selectinload(Invoice.payments))
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).unique())


class PaymentRepository(BaseRepository[Payment]):
    """Persistence for payments."""

    model = Payment

    def list_by_invoice(self, invoice_id: int) -> list[Payment]:
        stmt = (
            self._base_query()
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.paid_at.desc())
        )
        return list(self._session.scalars(stmt))

    def search(
        self,
        company_id: int,
        *,
        query: str | None = None,
        limit: int = 200,
    ) -> list[Payment]:
        """Search company payments joined to invoices, newest first."""
        stmt = (
            self._base_query()
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Payment.company_id == company_id, Invoice.deleted_at.is_(None))
            .options(selectinload(Payment.invoice))
            .order_by(Payment.paid_at.desc())
            .limit(limit)
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Invoice.number.ilike(pattern),
                    Payment.reference.ilike(pattern),
                    Payment.notes.ilike(pattern),
                )
            )
        return list(self._session.scalars(stmt).unique())

    def list_by_customer(self, customer_id: int, *, limit: int = 50) -> list[Payment]:
        """Return recent payments for a customer via invoice join."""
        stmt = (
            self._base_query()
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Invoice.customer_id == customer_id, Invoice.deleted_at.is_(None))
            .options(selectinload(Payment.invoice))
            .order_by(Payment.paid_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).unique())

    def sum_cash_for_session(self, cash_session_id: int) -> int:
        stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.cash_session_id == cash_session_id,
                Payment.deleted_at.is_(None),
                Payment.method == "cash",
            )
        )
        return int(self._session.scalar(stmt) or 0)


class CashSessionRepository(BaseRepository[CashSession]):
    """Persistence for cash sessions."""

    model = CashSession

    def get_open(self, company_id: int) -> CashSession | None:
        stmt = self._base_query().where(
            CashSession.company_id == company_id,
            CashSession.status == CashSessionStatus.OPEN.value,
        )
        return self._session.scalar(stmt)
