"""Finance application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.time import utc_now
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.finance.models.enums import (
    CashSessionStatus,
    InvoiceStatus,
    PaymentMethod,
)
from app.modules.finance.models.invoice import CashSession, Invoice, InvoiceLine, Payment
from app.modules.finance.repositories.finance_repository import (
    CashSessionRepository,
    InvoiceRepository,
    PaymentRepository,
)
from app.modules.finance.schemas.finance_schema import (
    CashSessionCloseSchema,
    CashSessionOpenSchema,
    InvoiceCreateSchema,
    PaymentCreateSchema,
)
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService


class FinanceService:
    """Invoices, payments, and cash register use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._invoices = InvoiceRepository(session)
        self._payments = PaymentRepository(session)
        self._cash = CashSessionRepository(session)
        self._customers = CustomerRepository(session)
        self._work_orders = WorkOrderRepository(session)
        self._audit = AuditService(session)

    def list_invoices(
        self,
        company_id: int,
        *,
        query: str | None = None,
        status: str | None = None,
    ) -> list[Invoice]:
        return self._invoices.search(company_id, query=query, status=status)

    def list_payments(
        self,
        company_id: int,
        *,
        query: str | None = None,
        limit: int = 200,
    ) -> list[Payment]:
        return self._payments.search(company_id, query=query, limit=limit)

    def list_invoices_for_customer(
        self,
        customer_id: int,
        *,
        limit: int = 50,
    ) -> list[Invoice]:
        return self._invoices.list_by_customer(customer_id, limit=limit)

    def list_payments_for_customer(
        self,
        customer_id: int,
        *,
        limit: int = 50,
    ) -> list[Payment]:
        return self._payments.list_by_customer(customer_id, limit=limit)

    def get_invoice(self, invoice_id: int) -> Invoice:
        invoice = self._invoices.get_with_details(invoice_id)
        if invoice is None:
            raise NotFoundError("Hisob-faktura topilmadi.", entity="Invoice")
        return invoice

    def create_invoice(
        self,
        company_id: int,
        payload: InvoiceCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Invoice:
        customer = self._customers.get_by_id(payload.customer_id)
        if customer is None or customer.company_id != company_id:
            raise NotFoundError("Mijoz topilmadi.", entity="Customer")

        if payload.work_order_id is not None:
            work_order = self._work_orders.get_by_id(payload.work_order_id)
            if work_order is None or work_order.company_id != company_id:
                raise ValidationError("Ish buyurtmasi topilmadi.")
            if work_order.customer_id != payload.customer_id:
                raise ValidationError("Ish buyurtmasi mijozga mos emas.")

        subtotal = sum(line.quantity * line.unit_price for line in payload.lines)
        if payload.discount_amount > subtotal:
            raise ValidationError("Chegirma summadan katta boʻlishi mumkin emas.")
        total = subtotal - payload.discount_amount + payload.tax_amount
        if total < 0:
            raise ValidationError("Jami summa manfiy boʻlishi mumkin emas.")

        number = self._generate_invoice_number(company_id)
        status = InvoiceStatus.ISSUED if payload.issue_immediately else InvoiceStatus.DRAFT
        invoice = Invoice(
            company_id=company_id,
            customer_id=payload.customer_id,
            work_order_id=payload.work_order_id,
            number=number,
            status=status.value,
            subtotal=subtotal,
            tax_amount=payload.tax_amount,
            discount_amount=payload.discount_amount,
            total_amount=total,
            paid_amount=0,
            notes=payload.notes,
            issued_at=utc_now() if payload.issue_immediately else None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._invoices.add(invoice)
        for line in payload.lines:
            self._session.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_total=line.quantity * line.unit_price,
                )
            )
        self._session.flush()
        self._audit.record(
            "invoice_created",
            actor_id=actor_id,
            entity_type="Invoice",
            entity_id=invoice.id,
            entity_uuid=invoice.uuid,
            message=invoice.number,
        )
        return invoice

    def create_invoice_from_work_order(
        self,
        company_id: int,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> Invoice:
        work_order = self._work_orders.get_by_id(work_order_id)
        if work_order is None or work_order.company_id != company_id:
            raise NotFoundError("Ish buyurtmasi topilmadi.", entity="WorkOrder")
        amount = work_order.final_cost or work_order.estimated_cost or 0
        if amount <= 0:
            raise ValidationError("Ish buyurtmasida narx koʻrsatilmagan.")
        payload = InvoiceCreateSchema(
            customer_id=work_order.customer_id,
            work_order_id=work_order.id,
            lines=[
                {
                    "description": f"Taʼmir — {work_order.number}",
                    "quantity": 1,
                    "unit_price": amount,
                }
            ],
            notes=work_order.problem_description,
            issue_immediately=True,
        )
        return self.create_invoice(company_id, payload, actor_id=actor_id)

    def void_invoice(self, invoice_id: int, *, actor_id: int | None = None) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status == InvoiceStatus.VOID.value:
            raise ValidationError("Hisob-faktura allaqachon bekor qilingan.")
        if invoice.paid_amount > 0:
            raise ValidationError("Toʻlov qilingan hisob-fakturani bekor qilib boʻlmaydi.")
        invoice.status = InvoiceStatus.VOID.value
        invoice.voided_at = utc_now()
        invoice.updated_by = actor_id
        self._invoices.save(invoice)
        self._audit.record(
            "invoice_voided",
            actor_id=actor_id,
            entity_type="Invoice",
            entity_id=invoice.id,
            entity_uuid=invoice.uuid,
        )
        return invoice

    def record_payment(
        self,
        company_id: int,
        payload: PaymentCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Payment:
        invoice = self.get_invoice(payload.invoice_id)
        if invoice.company_id != company_id:
            raise NotFoundError("Hisob-faktura topilmadi.", entity="Invoice")
        if invoice.status in {InvoiceStatus.DRAFT.value, InvoiceStatus.VOID.value}:
            raise ValidationError("Bu hisob-fakturaga toʻlov qabul qilinmaydi.")
        if payload.amount > invoice.balance_due:
            raise ValidationError("Toʻlov qoldiqdan katta boʻlishi mumkin emas.")

        cash_session_id = None
        if payload.method == PaymentMethod.CASH.value:
            session = self._cash.get_open(company_id)
            if session is None:
                raise ValidationError("Naqd toʻlov uchun kassa sessiyasi ochiq boʻlishi kerak.")
            cash_session_id = session.id

        payment = Payment(
            company_id=company_id,
            invoice_id=invoice.id,
            cash_session_id=cash_session_id,
            amount=payload.amount,
            method=payload.method,
            reference=payload.reference,
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._payments.add(payment)

        invoice.paid_amount += payload.amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID.value
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID.value
        invoice.updated_by = actor_id
        self._invoices.save(invoice)

        self._audit.record(
            "payment_recorded",
            actor_id=actor_id,
            entity_type="Payment",
            entity_id=payment.id,
            entity_uuid=payment.uuid,
            message=f"{invoice.number}:{payload.amount}",
        )
        return payment

    def get_open_cash_session(self, company_id: int) -> CashSession | None:
        return self._cash.get_open(company_id)

    def open_cash_session(
        self,
        company_id: int,
        payload: CashSessionOpenSchema,
        *,
        actor_id: int,
    ) -> CashSession:
        if self._cash.get_open(company_id) is not None:
            raise ConflictError("Allaqachon ochiq kassa sessiyasi bor.")
        session = CashSession(
            company_id=company_id,
            opened_by=actor_id,
            status=CashSessionStatus.OPEN.value,
            opening_balance=payload.opening_balance,
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._cash.add(session)
        self._audit.record(
            "cash_session_opened",
            actor_id=actor_id,
            entity_type="CashSession",
            entity_id=session.id,
            entity_uuid=session.uuid,
        )
        return session

    def close_cash_session(
        self,
        company_id: int,
        payload: CashSessionCloseSchema,
        *,
        actor_id: int,
    ) -> CashSession:
        session = self._cash.get_open(company_id)
        if session is None:
            raise ValidationError("Ochiq kassa sessiyasi yoʻq.")
        cash_in = self._payments.sum_cash_for_session(session.id)
        expected = session.opening_balance + cash_in
        session.status = CashSessionStatus.CLOSED.value
        session.closed_by = actor_id
        session.closed_at = utc_now()
        session.closing_balance = payload.closing_balance
        session.expected_cash = expected
        session.notes = payload.notes or session.notes
        session.updated_by = actor_id
        self._cash.save(session)
        self._audit.record(
            "cash_session_closed",
            actor_id=actor_id,
            entity_type="CashSession",
            entity_id=session.id,
            entity_uuid=session.uuid,
            message=f"expected={expected};actual={payload.closing_balance}",
        )
        return session

    def _generate_invoice_number(self, company_id: int) -> str:
        today = utc_now().strftime("%Y%m%d")
        prefix = f"INV-{today}-"
        seq = self._invoices.next_sequence(company_id, prefix)
        return f"{prefix}{seq:04d}"
