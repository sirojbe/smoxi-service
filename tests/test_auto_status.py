"""Auto status progression after approval."""

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
from app.modules.work_orders.schemas.work_order_schema import WorkOrderStatusChangeSchema
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


def test_approve_without_parts_goes_to_repairing(db_session: Session) -> None:
    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901110011",
            device_model="A1",
            problem_description="Buzilgan",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    order = WorkOrderService(db_session).change_status(
        intake.work_order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        actor_id=1,
        auto_advance=True,
    )
    db_session.commit()
    assert order.status == WorkOrderStatus.REPAIRING.value


def test_approve_with_unlinked_parts_goes_to_waiting(db_session: Session) -> None:
    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901110022",
            device_model="B1",
            problem_description="Ekran",
            estimated_cost=10_000,
            parts=[
                {
                    "name": "Ekran",
                    "cost_price": 100_000,
                    "sale_price": 200_000,
                    "quantity": 1,
                }
            ],
        ),
        actor_id=1,
    )
    order = WorkOrderService(db_session).change_status(
        intake.work_order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        actor_id=1,
        auto_advance=True,
    )
    db_session.commit()
    assert order.status == WorkOrderStatus.WAITING_PARTS.value
