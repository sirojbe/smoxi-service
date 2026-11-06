"""Mark ready + sequential WO numbers + cancel/delete."""

from __future__ import annotations

import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import NotFoundError
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


def test_work_order_number_is_sequential(db_session: Session) -> None:
    service = QuickIntakeService(db_session)
    first = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998901000001",
            device_model="A",
            problem_description="Ekran nosoz",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    second = service.intake(
        1,
        QuickIntakeSchema(
            phone="+998901000002",
            device_model="B",
            problem_description="Batareya nosoz",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    db_session.commit()
    assert re.fullmatch(r"WO-\d{6}", first.work_order.number)
    assert re.fullmatch(r"WO-\d{6}", second.work_order.number)
    assert int(second.work_order.number.split("-")[1]) == int(
        first.work_order.number.split("-")[1]
    ) + 1


def test_mark_ready_from_repairing(db_session: Session) -> None:
    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901000003",
            device_model="C",
            problem_description="Kamera nosoz",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    wo = WorkOrderService(db_session)
    wo.change_status(
        intake.work_order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        actor_id=1,
        notify=False,
        auto_advance=True,
    )
    result = wo.mark_ready(intake.work_order.id, actor_id=1)
    db_session.commit()
    assert result.work_order.status == WorkOrderStatus.READY.value
    assert result.telegram_reason in {"no_token", "no_chat", "sent", "skipped"}


def test_cancel_and_soft_delete_early_order(db_session: Session) -> None:
    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901000099",
            device_model="Test",
            problem_description="Xato kiritildi",
            estimated_cost=10_000,
        ),
        actor_id=1,
    )
    wo = WorkOrderService(db_session)
    cancelled = wo.cancel_work_order(
        intake.work_order.id,
        note="Xato kiritilgan",
        actor_id=1,
    )
    assert cancelled.status == WorkOrderStatus.CANCELLED.value
    wo.soft_delete_work_order(intake.work_order.id, actor_id=1)
    db_session.commit()
    try:
        wo.get_work_order(intake.work_order.id)
        raise AssertionError("soft-deleted order should not load")
    except NotFoundError:
        pass


def test_mark_delivered_from_ready(db_session: Session) -> None:
    from app.core.exceptions import ValidationError

    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901000088",
            device_model="DeliverPhone",
            problem_description="Ekran",
            estimated_cost=50_000,
        ),
        actor_id=1,
    )
    wo = WorkOrderService(db_session)
    wo.change_status(
        intake.work_order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        actor_id=1,
        notify=False,
        auto_advance=True,
    )
    wo.mark_ready(intake.work_order.id, actor_id=1)
    delivered = wo.mark_delivered(intake.work_order.id, actor_id=1)
    db_session.commit()
    assert delivered.work_order.status == WorkOrderStatus.DELIVERED.value
    assert delivered.work_order.delivered_at is not None
    again = wo.mark_delivered(intake.work_order.id, actor_id=1)
    assert again.telegram_reason == "already_delivered"

    early = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901000089",
            device_model="Early",
            problem_description="Test",
            estimated_cost=1_000,
        ),
        actor_id=1,
    )
    with pytest.raises(ValidationError):
        wo.mark_delivered(early.work_order.id, actor_id=1)


def test_delivered_leaves_active_board_and_appears_in_reports(db_session: Session) -> None:
    from app.modules.reports.services.report_service import ReportService

    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901000077",
            device_model="BoardPhone",
            problem_description="Batareya",
            estimated_cost=20_000,
        ),
        actor_id=1,
    )
    wo = WorkOrderService(db_session)
    wo.change_status(
        intake.work_order.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        actor_id=1,
        notify=False,
        auto_advance=True,
    )
    wo.mark_ready(intake.work_order.id, actor_id=1)
    assert any(o.id == intake.work_order.id for o in wo.list_work_orders(1))
    wo.mark_delivered(intake.work_order.id, actor_id=1)
    db_session.commit()
    assert all(o.id != intake.work_order.id for o in wo.list_work_orders(1))
    delivered = wo.list_work_orders(1, status=WorkOrderStatus.DELIVERED.value)
    assert any(o.id == intake.work_order.id for o in delivered)
    report = ReportService(db_session).period_report(1, days=30)
    assert report.work_orders_delivered >= 1
    assert any(r.number == intake.work_order.number for r in report.work_orders)
