"""Finance service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.finance.models.enums import InvoiceStatus, PaymentMethod
from app.modules.finance.schemas.finance_schema import (
    CashSessionOpenSchema,
    InvoiceCreateSchema,
    InvoiceLineSchema,
    PaymentCreateSchema,
)
from app.modules.finance.services.finance_service import FinanceService
from app.services.bootstrap_service import BootstrapService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    BootstrapService(session).ensure_system_data()
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def customer_id(db_session: Session) -> int:
    customer = CustomerService(db_session).create_customer(
        1,
        CustomerCreateSchema(display_name="Moliya Mijoz", phone="+998907771122"),
        actor_id=1,
    )
    db_session.commit()
    return customer.id


def test_invoice_and_payment_flow(db_session: Session, customer_id: int) -> None:
    finance = FinanceService(db_session)
    finance.open_cash_session(
        1,
        CashSessionOpenSchema(opening_balance=100000),
        actor_id=1,
    )
    invoice = finance.create_invoice(
        1,
        InvoiceCreateSchema(
            customer_id=customer_id,
            lines=[InvoiceLineSchema(description="Ekran almashtirish", quantity=1, unit_price=500000)],
            discount_amount=0,
            tax_amount=0,
        ),
        actor_id=1,
    )
    assert invoice.status == InvoiceStatus.ISSUED.value
    finance.record_payment(
        1,
        PaymentCreateSchema(
            invoice_id=invoice.id,
            amount=200000,
            method=PaymentMethod.CASH.value,
        ),
        actor_id=1,
    )
    finance.record_payment(
        1,
        PaymentCreateSchema(
            invoice_id=invoice.id,
            amount=300000,
            method=PaymentMethod.CARD.value,
        ),
        actor_id=1,
    )
    db_session.commit()
    loaded = finance.get_invoice(invoice.id)
    assert loaded.status == InvoiceStatus.PAID.value
    assert loaded.paid_amount == 500000


def test_cash_required_for_cash_payment(db_session: Session, customer_id: int) -> None:
    finance = FinanceService(db_session)
    invoice = finance.create_invoice(
        1,
        InvoiceCreateSchema(
            customer_id=customer_id,
            lines=[InvoiceLineSchema(description="Diagnostika", quantity=1, unit_price=50000)],
        ),
        actor_id=1,
    )
    with pytest.raises(ValidationError):
        finance.record_payment(
            1,
            PaymentCreateSchema(
                invoice_id=invoice.id,
                amount=50000,
                method=PaymentMethod.CASH.value,
            ),
            actor_id=1,
        )
