"""Administration service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.administration.services.admin_service import AdministrationService
from app.services.audit_service import AuditService
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


def test_list_audit_returns_recorded_entries(db_session: Session) -> None:
    AuditService(db_session).record(
        "test.action",
        actor_id=1,
        entity_type="Customer",
        entity_id=1,
        message="Sinov yozuvi",
    )
    db_session.commit()
    rows = AdministrationService(db_session).list_audit(query="sinov")
    assert len(rows) >= 1
    assert any(r.action == "test.action" for r in rows)


def test_sidebar_includes_customers_and_admin() -> None:
    from app.ui.shell.sidebar import Sidebar

    route_ids = [r[0] for r in Sidebar.ROUTES]
    assert "customers" in route_ids
    assert "administration" in route_ids
    assert route_ids.index("customers") < route_ids.index("reception")
