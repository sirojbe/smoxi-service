"""CX-A timeline and QR tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.cx.models.events import EVENT_DEVICE_RECEIVED
from app.modules.cx.services.timeline_service import TimelineService
from app.modules.cx.services.wo_qr_service import WorkOrderQrService, build_qr_payload
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.schemas.work_order_schema import (
    WorkOrderCreateSchema,
    WorkOrderStatusChangeSchema,
)
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.services.bootstrap_service import BootstrapService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
        CustomerCreateSchema(display_name="CX Test", phone="+998909998877"),
        actor_id=1,
    )
    db_session.commit()
    return customer.id


def test_create_wo_writes_timeline_and_qr_token(
    db_session: Session, customer_id: int
) -> None:
    service = WorkOrderService(db_session)
    wo = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="Ekran ishlamayapti test",
            priority="normal",
        ),
        actor_id=1,
    )
    db_session.commit()
    assert wo.public_token
    events = TimelineService(db_session).list_events(wo.id)
    codes = {e.event_code for e in events}
    assert EVENT_DEVICE_RECEIVED in codes
    payload = build_qr_payload(wo, company_code="smoxi")
    assert wo.number in payload
    assert wo.public_token in payload


def test_status_change_appends_timeline(
    db_session: Session, customer_id: int
) -> None:
    service = WorkOrderService(db_session)
    wo = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="Batareya almashtirish testi",
            priority="normal",
        ),
        actor_id=1,
    )
    service.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(
            to_status=WorkOrderStatus.WAITING_DIAGNOSIS.value,
            note="Navbat",
        ),
        actor_id=1,
        notify=False,
    )
    db_session.commit()
    events = TimelineService(db_session).list_events(wo.id)
    assert len(events) >= 2


def test_qr_ensure_idempotent(db_session: Session, customer_id: int) -> None:
    service = WorkOrderService(db_session)
    wo = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="QR idempotent test case xx",
            priority="normal",
        ),
        actor_id=1,
    )
    db_session.commit()
    qr = WorkOrderQrService(db_session)
    t1 = qr.ensure_public_token(wo, actor_id=1)
    t2 = qr.ensure_public_token(wo, actor_id=1)
    assert t1 == t2
