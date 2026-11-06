"""Technician and report service tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema, DeviceCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.reports.services.report_service import ReportService
from app.modules.technicians.schemas.technician_schema import TechnicianCreateSchema
from app.modules.technicians.services.technician_service import TechnicianService
from app.modules.work_orders.schemas.work_order_schema import WorkOrderCreateSchema
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


def test_assign_technician(db_session: Session) -> None:
    customers = CustomerService(db_session)
    customer = customers.create_customer(
        1,
        CustomerCreateSchema(display_name="WO Mijoz", phone="+998901000001"),
        actor_id=1,
    )
    device = customers.create_device(
        customer.id,
        DeviceCreateSchema(model="Redmi Note", brand="Xiaomi"),
        actor_id=1,
    )
    tech = TechnicianService(db_session).create_technician(
        1,
        TechnicianCreateSchema(code="T01", full_name="Usta Ali", skills="telefon"),
        actor_id=1,
    )
    order = WorkOrderService(db_session).create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer.id,
            device_id=device.id,
            problem_description="Sensor ishlamayapti",
        ),
        actor_id=1,
    )
    TechnicianService(db_session).assign_to_work_order(order.id, tech.id, actor_id=1)
    db_session.commit()
    loaded = WorkOrderService(db_session).get_work_order(order.id)
    assert loaded.technician_id == tech.id


def test_report_exports(db_session: Session, tmp_path: Path) -> None:
    from datetime import date, timedelta

    stats = ReportService(db_session).dashboard_stats(1)
    assert stats.customers_total >= 0
    today = date.today()
    report = ReportService(db_session).period_report(
        1,
        days=None,
        from_day=today - timedelta(days=7),
        to_day=today,
    )
    assert report.work_orders_created >= 0
    xlsx = ReportService(db_session).export_excel(
        1,
        tmp_path / "report.xlsx",
        days=None,
        from_day=today - timedelta(days=7),
        to_day=today,
    )
    pdf = ReportService(db_session).export_pdf(1, tmp_path / "report.pdf", days=7)
    assert xlsx.exists()
    assert pdf.exists()
