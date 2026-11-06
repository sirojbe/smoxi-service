"""Quick intake service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.reception.services.quick_intake_service import (
    QuickIntakeSchema,
    QuickIntakeService,
)
from app.modules.work_orders.models.status import WorkOrderStatus
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


def test_quick_intake_creates_customer_and_waits_approval(db_session: Session) -> None:
    service = QuickIntakeService(db_session)
    result = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998901112233",
            display_name="Ali",
            device_model="iPhone 13",
            device_brand="Apple",
            problem_description="Ekran yorilgan",
            work_scope="Ekran almashtirish",
            estimated_cost=10_000,
            parts=[
                {"name": "Ekran moduli", "cost_price": 180_000, "sale_price": 280_000, "quantity": 1}
            ],
        ),
        actor_id=1,
    )
    db_session.commit()
    assert result.created_customer is True
    assert result.customer.id > 0
    assert result.work_order.number.startswith("WO-")
    assert result.work_order.status == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value
    assert result.expense_total == 180_000
    assert result.customer_total == 10_000 + 280_000
    assert result.telegram_sent is False


def test_quick_intake_reuses_customer_by_phone(db_session: Session) -> None:
    service = QuickIntakeService(db_session)
    first = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998909998877",
            device_model="Redmi 12",
            problem_description="Batareya",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    second = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998909998877",
            device_model="Redmi 12 Pro",
            problem_description="Kamera",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    db_session.commit()
    assert first.customer.id == second.customer.id
    assert second.created_customer is False
    assert second.expense_total == 0


def test_quick_intake_restores_soft_deleted_customer(db_session: Session) -> None:
    from app.modules.customers.repositories.customer_repository import CustomerRepository

    service = QuickIntakeService(db_session)
    first = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998915665559",
            display_name="Sirojbek",
            device_model="Phone A",
            problem_description="Nosozlik bir",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    customer_id = first.customer.id
    CustomerRepository(db_session).soft_delete(first.customer, actor_id=1)
    db_session.commit()

    second = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998915665559",
            display_name="Sirojbek",
            device_model="Phone B",
            problem_description="Nosozlik ikki",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    db_session.commit()
    assert second.customer.id == customer_id
    assert second.customer.deleted_at is None
