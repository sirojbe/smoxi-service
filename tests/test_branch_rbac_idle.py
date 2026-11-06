"""Branch filter, RBAC routes, idle prefs tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.branches.services.branch_service import BranchCreateSchema, BranchService
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.work_orders.schemas.work_order_schema import WorkOrderCreateSchema
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.security.permissions import INVENTORY_VIEW, WORK_ORDERS_VIEW
from app.security.route_permissions import allowed_routes
from app.services.bootstrap_service import BootstrapService
from app.ui.shell.shell_prefs import ShellPrefs, load_shell_prefs, save_shell_prefs


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


def test_work_order_branch_filter(db_session: Session) -> None:
    branches = BranchService(db_session)
    main = branches.ensure_default(1)
    other = branches.create_branch(
        1, BranchCreateSchema(code="B2", name="Ikkinchi"), actor_id=1
    )
    customer = CustomerService(db_session).create_customer(
        1,
        CustomerCreateSchema(display_name="Test", phone="+998901000001"),
        actor_id=1,
    )
    wo = WorkOrderService(db_session)
    a = wo.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer.id,
            branch_id=main.id,
            problem_description="Ekran ishlamayapti test",
        ),
        actor_id=1,
    )
    b = wo.create_from_reception(
        1,
        WorkOrderCreateSchema(
            customer_id=customer.id,
            branch_id=other.id,
            problem_description="Batareya almashtirish test",
        ),
        actor_id=1,
    )
    db_session.commit()
    only_main = wo.list_work_orders(1, branch_id=main.id)
    ids = {x.id for x in only_main}
    assert a.id in ids
    # other branch WO excluded unless null
    assert b.id not in ids
    all_rows = wo.list_work_orders(1, branch_id=None)
    assert {a.id, b.id}.issubset({x.id for x in all_rows})


def test_allowed_routes_for_warehouse_role() -> None:
    allowed = allowed_routes({INVENTORY_VIEW, "dashboard.view", "inventory.manage"})
    assert "inventory" in allowed
    assert "warehouse" in allowed
    assert "work_orders" not in allowed
    assert "logout" in allowed
    assert "help" in allowed


def test_allowed_routes_work_orders() -> None:
    allowed = allowed_routes({WORK_ORDERS_VIEW, "dashboard.view"})
    assert "work_orders" in allowed
    assert "finance" not in allowed


def test_shell_prefs_roundtrip(tmp_path, monkeypatch) -> None:
    # QSettings uses org/app; just ensure save/load API works
    save_shell_prefs(ShellPrefs(idle_lock_minutes=7))
    prefs = load_shell_prefs()
    assert prefs.idle_lock_minutes == 7
    save_shell_prefs(ShellPrefs(idle_lock_minutes=10))
