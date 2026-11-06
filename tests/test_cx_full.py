"""CX B–H integration tests: intake, media, quote, reservation, warranty, KPI."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.cx.models.events import EVENT_ADMIN_OVERRIDE, EVENT_WARRANTY_STARTED
from app.modules.cx.services.intake_service import IntakeService
from app.modules.cx.services.kpi_service import TechnicianKpiService
from app.modules.cx.services.media_service import MediaService
from app.modules.cx.services.quote_service import QuoteService
from app.modules.cx.services.reservation_service import ReservationService
from app.modules.cx.services.timeline_service import TimelineService
from app.modules.cx.services.warranty_service import WarrantyService
from app.modules.inventory.schemas.item_schema import InventoryItemCreateSchema
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.reception.services.quick_intake_service import (
    QuickIntakeSchema,
    QuickIntakeService,
)
from app.modules.technicians.schemas.technician_schema import TechnicianCreateSchema
from app.modules.technicians.services.technician_service import TechnicianService
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.schemas.work_order_schema import (
    WorkOrderCreateSchema,
    WorkOrderPartSchema,
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
        CustomerCreateSchema(display_name="CX Full", phone="+998901112233"),
        actor_id=1,
    )
    db_session.commit()
    return customer.id


def test_intake_snapshot_and_signature_and_pdf(
    db_session: Session, customer_id: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SMOXI_UPLOADS_DIR", str(tmp_path))
    from app.config.settings import get_settings

    get_settings.cache_clear()
    try:
        wo = WorkOrderService(db_session).create_from_reception(
            1,
            WorkOrderCreateSchema(
                customer_id=customer_id,
                problem_description="Ekran yorilgan test",
            ),
            actor_id=1,
        )
        intake = IntakeService(db_session)
        snap = intake.save_snapshot(
            wo.id,
            actor_id=1,
            imei="123456789012345",
            screen_condition="yoriq",
            body_condition="yaxshi",
        )
        db_session.commit()
        assert snap.imei == "123456789012345"

        # Minimal non-empty PNG-ish bytes for signature lock
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        # Write via pad path: capture_signature expects bytes and writes temp
        sig = intake.capture_signature(wo.id, png, actor_id=1)
        db_session.commit()
        assert sig.is_locked
        with pytest.raises(ValidationError):
            intake.capture_signature(wo.id, png, actor_id=1)

        doc = intake.generate_receipt_pdf(wo.id, actor_id=1)
        db_session.commit()
        assert doc.doc_version == 1
        assert (tmp_path / doc.file_path).is_file() or Path(
            get_settings().uploads_dir, doc.file_path
        ).is_file()
    finally:
        get_settings.cache_clear()


def test_media_add_photo(
    db_session: Session, customer_id: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SMOXI_UPLOADS_DIR", str(tmp_path))
    from app.config.settings import get_settings

    get_settings.cache_clear()
    try:
        wo = WorkOrderService(db_session).create_from_reception(
            1,
            WorkOrderCreateSchema(
                customer_id=customer_id,
                problem_description="Kamera nosoz test",
            ),
            actor_id=1,
        )
        src = tmp_path / "front.jpg"
        src.write_bytes(b"fake-jpeg-bytes")
        asset = MediaService(db_session).add_photo(
            wo.id, src, category="front", actor_id=1
        )
        db_session.commit()
        assert asset.media_type == "photo"
        listed = MediaService(db_session).list_media(wo.id)
        assert len(listed) == 1
    finally:
        get_settings.cache_clear()


def test_repair_blocked_without_approval(
    db_session: Session, customer_id: int
) -> None:
    service = WorkOrderService(db_session)
    wo = service.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="Quloqlik ishlamaydi",
        ),
        actor_id=1,
    )
    service.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.DIAGNOSING.value),
        actor_id=1,
        notify=False,
        auto_advance=False,
    )
    service.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.WAITING_PARTS.value),
        actor_id=1,
        notify=False,
        auto_advance=False,
    )
    with pytest.raises(ValidationError):
        service.change_status(
            wo.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.REPAIRING.value),
            actor_id=1,
            notify=False,
            auto_advance=False,
        )


def test_admin_override_starts_repair(db_session: Session) -> None:
    intake = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998909998811",
            device_model="OverridePhone",
            problem_description="Tezkor taʼmir kerak",
            estimated_cost=50_000,
        ),
        actor_id=1,
    )
    QuoteService(db_session).start_repair_with_override(
        intake.work_order.id,
        reason="Mijoz telefon orqali rozilik berdi",
        actor_id=1,
    )
    db_session.commit()
    wo = WorkOrderService(db_session).get_work_order(intake.work_order.id)
    assert wo.status == WorkOrderStatus.REPAIRING.value
    codes = {e.event_code for e in TimelineService(db_session).list_events(wo.id)}
    assert EVENT_ADMIN_OVERRIDE in codes


def test_reservation_and_consume(
    db_session: Session, customer_id: int
) -> None:
    inv = InventoryService(db_session)
    item = inv.create_item(
        1,
        InventoryItemCreateSchema(
            sku="CX-BAT-01",
            name="Batareya CX",
            quantity_on_hand=5,
            sale_price=100_000,
        ),
        actor_id=1,
    )
    wo_svc = WorkOrderService(db_session)
    wo = wo_svc.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="Batareya almashtirish",
            parts=[
                WorkOrderPartSchema(
                    name="Batareya CX",
                    quantity=1,
                    sale_price=100_000,
                    inventory_item_id=item.id,
                )
            ],
        ),
        actor_id=1,
    )
    # Move to approved path
    wo_svc.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.DIAGNOSING.value),
        notify=False,
        auto_advance=False,
        actor_id=1,
    )
    wo_svc.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(
            to_status=WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value
        ),
        notify=False,
        auto_advance=False,
        actor_id=1,
    )
    wo_svc.change_status(
        wo.id,
        WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
        notify=False,
        auto_advance=True,
        actor_id=1,
    )
    db_session.commit()
    reserved = ReservationService(db_session)._get_open(wo.id, item.id)  # noqa: SLF001
    assert reserved is not None
    assert reserved.status == "reserved"

    # Advance to READY to consume
    current = WorkOrderService(db_session).get_work_order(wo.id)
    # Ensure repairing then chain to ready
    if current.status == WorkOrderStatus.WAITING_PARTS.value:
        WorkOrderService(db_session).change_status(
            wo.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.REPAIRING.value),
            notify=False,
            auto_advance=False,
            actor_id=1,
        )
    WorkOrderService(db_session).mark_ready(wo.id, actor_id=1)
    db_session.commit()
    item2 = InventoryService(db_session).get_item(item.id)
    assert item2.quantity_on_hand == 4


def test_warranty_on_delivered(
    db_session: Session, customer_id: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SMOXI_UPLOADS_DIR", str(tmp_path))
    from app.config.settings import get_settings

    get_settings.cache_clear()
    try:
        intake = QuickIntakeService(db_session).intake(
            1,
            QuickIntakeSchema(
                phone="+998907776655",
                device_model="WarrantyPhone",
                problem_description="Kafolat testi",
                estimated_cost=20_000,
            ),
            actor_id=1,
        )
        wo = WorkOrderService(db_session)
        wo.change_status(
            intake.work_order.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.APPROVED.value),
            notify=False,
            auto_advance=True,
            actor_id=1,
        )
        wo.mark_ready(intake.work_order.id, actor_id=1)
        wo.change_status(
            intake.work_order.id,
            WorkOrderStatusChangeSchema(to_status=WorkOrderStatus.DELIVERED.value),
            notify=False,
            auto_advance=False,
            actor_id=1,
        )
        db_session.commit()
        card = WarrantyService(db_session).get_for_work_order(intake.work_order.id)
        assert card is not None
        assert card.warranty_number.startswith("WR-")
        codes = {
            e.event_code
            for e in TimelineService(db_session).list_events(intake.work_order.id)
        }
        assert EVENT_WARRANTY_STARTED in codes
    finally:
        get_settings.cache_clear()


def test_kpi_leaderboard(db_session: Session, customer_id: int) -> None:
    tech = TechnicianService(db_session).create_technician(
        1,
        TechnicianCreateSchema(code="T-CX", full_name="CX Texnik"),
        actor_id=1,
    )
    wo = WorkOrderService(db_session).create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer_id,
            problem_description="KPI test buyurtma",
            estimated_cost=100_000,
        ),
        actor_id=1,
    )
    wo.technician_id = tech.id
    db_session.flush()
    db_session.commit()
    rows = TechnicianKpiService(db_session).leaderboard(1)
    assert any(r.technician_id == tech.id and r.assigned >= 1 for r in rows)


def test_quick_intake_saves_cx_fields(db_session: Session) -> None:
    result = QuickIntakeService(db_session).intake(
        1,
        QuickIntakeSchema(
            phone="+998901234400",
            device_model="iPhone 12",
            problem_description="Sensor ishlamaydi",
            estimated_cost=150_000,
            imei="356938035643809",
            screen_condition="yoriq",
            body_condition="yaxshi",
            customer_email="mijoz@example.com",
        ),
        actor_id=1,
    )
    db_session.commit()
    snap = IntakeService(db_session).get_snapshot(result.work_order.id)
    assert snap is not None
    assert snap.imei == "356938035643809"
    assert snap.screen_condition == "yoriq"
