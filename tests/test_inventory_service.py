"""Inventory service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.inventory.models.enums import StockMovementType
from app.modules.inventory.schemas.item_schema import (
    InventoryItemCreateSchema,
    StockAdjustSchema,
)
from app.modules.inventory.services.inventory_service import InventoryService
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


def test_create_item_and_stock_out(db_session: Session) -> None:
    service = InventoryService(db_session)
    item = service.create_item(
        1,
        InventoryItemCreateSchema(
            sku="SCR-IPH13",
            name="iPhone 13 ekran",
            quantity_on_hand=5,
            min_quantity=2,
            sale_price=450000,
        ),
        actor_id=1,
    )
    service.adjust_stock(
        item.id,
        StockAdjustSchema(movement_type=StockMovementType.OUT.value, quantity=2, reason="WO"),
        actor_id=1,
    )
    db_session.commit()
    updated = service.get_item(item.id)
    assert updated.quantity_on_hand == 3
    assert len(service.list_movements(item.id)) >= 2


def test_negative_stock_blocked(db_session: Session) -> None:
    service = InventoryService(db_session)
    item = service.create_item(
        1,
        InventoryItemCreateSchema(sku="BAT-01", name="Batareya", quantity_on_hand=1),
        actor_id=1,
    )
    with pytest.raises(ValidationError):
        service.adjust_stock(
            item.id,
            StockAdjustSchema(movement_type=StockMovementType.OUT.value, quantity=5),
            actor_id=1,
        )
