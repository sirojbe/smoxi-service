"""Branch, lock, warehouse tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import AuthenticationError
from app.models.base import Base
from app.modules.auth.services.auth_service import AuthService
from app.modules.branches.services.branch_service import BranchCreateSchema, BranchService
from app.modules.inventory.schemas.item_schema import InventoryItemCreateSchema
from app.modules.inventory.services.inventory_service import InventoryService
from app.services.bootstrap_service import BootstrapService
from app.ui.shell.sidebar import Sidebar


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


def test_default_branch_and_create(db_session: Session) -> None:
    svc = BranchService(db_session)
    main = svc.ensure_default(1)
    assert main.code == "MAIN"
    second = svc.create_branch(
        1,
        BranchCreateSchema(code="CHL", name="Chilonzor"),
        actor_id=1,
    )
    db_session.commit()
    assert second.id != main.id
    assert len(svc.list_branches(1)) >= 2


def test_verify_user_password(db_session: Session) -> None:
    auth = AuthService(db_session)
    user = auth.verify_user_password(1, "1234")
    assert user.username == "1"
    with pytest.raises(AuthenticationError):
        auth.verify_user_password(1, "wrong")


def test_warehouse_transfer(db_session: Session) -> None:
    inv = InventoryService(db_session)
    main = inv.ensure_default_warehouse(1, actor_id=1)
    other = inv.create_warehouse(
        1, code="WH2", name="Ikkinchi ombor", actor_id=1
    )
    item = inv.create_item(
        1,
        InventoryItemCreateSchema(
            sku="SKU-TR",
            name="Test part",
            quantity_on_hand=10,
            warehouse_id=main.id,
        ),
        actor_id=1,
    )
    inv.transfer_stock(item.id, to_warehouse_id=other.id, quantity=10, actor_id=1)
    db_session.commit()
    moved = inv.get_item(item.id)
    assert moved.warehouse_id == other.id
    assert moved.quantity_on_hand == 10


def test_sidebar_warehouse_route() -> None:
    routes = [r[0] for r in Sidebar.ROUTES]
    assert "warehouse" in routes
    assert routes.index("inventory") < routes.index("warehouse")
