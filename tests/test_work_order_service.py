"""Work order service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema, DeviceCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.schemas.work_order_schema import (
    WorkOrderCreateSchema,
    WorkOrderStatusChangeSchema,
)
from app.modules.work_orders.services.work_order_service import WorkOrderService
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
def customer_with_device(db_session: Session) -> tuple[int, int]:
    customers = CustomerService(db_session)
    customer = customers.create_customer(
        1,
        CustomerCreateSchema(display_name="Test Mijoz", phone="+998901234567"),
        actor_id=1,
    )
    device = customers.create_device(
        customer.id,
        DeviceCreateSchema(model="Galaxy A54", brand="Samsung"),
        actor_id=1,
    )
    db_session.commit()
    return customer.id, device.id


def test_create_work_order(db_session: Session, customer_with_device: tuple[int, int]) -> None:
    customer_id, device_id = customer_with_device
    service = WorkOrderService(db_session)
    order = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            device_id=device_id,
            problem_description="Ekran yorilgan",
        ),
        actor_id=1,
    )
    db_session.commit()
    assert order.number.startswith("WO-")
    assert order.status == WorkOrderStatus.RECEIVED.value
    loaded = service.get_work_order(order.id)
    assert len(loaded.status_history) == 1


def test_status_transition_and_illegal(db_session: Session, customer_with_device: tuple[int, int]) -> None:
    customer_id, device_id = customer_with_device
    service = WorkOrderService(db_session)
    order = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            device_id=device_id,
            problem_description="Zaryad olmaydi",
        ),
        actor_id=1,
    )
    service.change_status(
        order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.DIAGNOSING.value),
        actor_id=1,
    )
    db_session.commit()
    updated = service.get_work_order(order.id)
    assert updated.status == WorkOrderStatus.DIAGNOSING.value

    with pytest.raises(ValidationError):
        service.change_status(
            order.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.READY.value),
            actor_id=1,
        )


def test_cancel_requires_note(db_session: Session, customer_with_device: tuple[int, int]) -> None:
    customer_id, device_id = customer_with_device
    service = WorkOrderService(db_session)
    order = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            device_id=device_id,
            problem_description="Suvga tushgan",
        ),
        actor_id=1,
    )
    with pytest.raises(ValidationError):
        service.change_status(
            order.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.CANCELLED.value),
            actor_id=1,
        )
