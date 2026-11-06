"""Supplier and purchase order service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.inventory.schemas.item_schema import InventoryItemCreateSchema
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.suppliers.models.enums import PurchaseOrderStatus
from app.modules.suppliers.schemas.supplier_schema import (
    PurchaseOrderCreateSchema,
    PurchaseOrderLineSchema,
    SupplierCreateSchema,
)
from app.modules.suppliers.services.supplier_service import SupplierService
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


def test_create_supplier_and_receive_po(db_session: Session) -> None:
    suppliers = SupplierService(db_session)
    inventory = InventoryService(db_session)

    supplier = suppliers.create_supplier(
        1,
        SupplierCreateSchema(code="SUP-01", name="Parts Hub", phone="+998901112233"),
        actor_id=1,
    )
    item = inventory.create_item(
        1,
        InventoryItemCreateSchema(
            sku="SCR-01",
            name="Ekran",
            quantity_on_hand=2,
            purchase_price=100000,
        ),
        actor_id=1,
    )
    order = suppliers.create_purchase_order(
        1,
        PurchaseOrderCreateSchema(
            supplier_id=supplier.id,
            lines=[
                PurchaseOrderLineSchema(
                    inventory_item_id=item.id,
                    quantity=3,
                    unit_cost=95000,
                )
            ],
            submit=True,
        ),
        actor_id=1,
    )
    assert order.status == PurchaseOrderStatus.ORDERED.value
    assert order.total_amount == 285000
    assert len(order.lines) == 1

    suppliers.receive_purchase_order(order.id, actor_id=1)
    db_session.commit()

    received = suppliers.get_purchase_order(order.id)
    assert received.status == PurchaseOrderStatus.RECEIVED.value
    assert inventory.get_item(item.id).quantity_on_hand == 5


def test_cancel_blocks_receive(db_session: Session) -> None:
    suppliers = SupplierService(db_session)
    inventory = InventoryService(db_session)
    supplier = suppliers.create_supplier(
        1,
        SupplierCreateSchema(code="SUP-02", name="Cancel Co"),
        actor_id=1,
    )
    item = inventory.create_item(
        1,
        InventoryItemCreateSchema(sku="BAT-02", name="Batareya", quantity_on_hand=0),
        actor_id=1,
    )
    order = suppliers.create_purchase_order(
        1,
        PurchaseOrderCreateSchema(
            supplier_id=supplier.id,
            lines=[
                PurchaseOrderLineSchema(
                    inventory_item_id=item.id,
                    quantity=1,
                    unit_cost=50000,
                )
            ],
        ),
        actor_id=1,
    )
    suppliers.cancel_purchase_order(order.id, actor_id=1)
    with pytest.raises(ValidationError):
        suppliers.receive_purchase_order(order.id, actor_id=1)
