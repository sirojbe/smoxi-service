"""HTTP API v1 and sync foundation tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.app import create_api_app
from app.core.enums import SyncStatus
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.sync.services.sync_service import SyncService
from app.plugins.registry import plugin_registry
from app.services.bootstrap_service import BootstrapService


@dataclass
class _FakeContainer:
    session_factory: sessionmaker[Session]

    def create_session(self) -> Session:
        return self.session_factory()


@pytest.fixture()
def factory() -> sessionmaker[Session]:
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
    session.close()
    return factory


@pytest.fixture()
def client(factory: sessionmaker[Session]) -> TestClient:
    app = create_api_app(_FakeContainer(factory))  # type: ignore[arg-type]
    return TestClient(app)


def test_health(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["api"] == "v1"


def test_login_and_me(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"company_code": "smoxi", "username": "1", "password": "1234"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "1"


def test_work_orders_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/work-orders").status_code == 401


def test_sync_pull_and_push(factory: sessionmaker[Session], client: TestClient) -> None:
    db = factory()
    try:
        CustomerService(db).create_customer(
            1,
            CustomerCreateSchema(display_name="API Sync", phone="+998901112233"),
            actor_id=1,
        )
        db.commit()
    finally:
        db.close()

    login = client.post(
        "/api/v1/auth/login",
        json={"company_code": "smoxi", "username": "1", "password": "1234"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    pull = client.get("/api/v1/sync/pull", headers=headers)
    assert pull.status_code == 200
    entities = pull.json()["entities"]
    assert any(e["entity_type"] == "customer" for e in entities)

    acks = [
        {
            "entity_type": e["entity_type"],
            "uuid": e["uuid"],
            "version": e["version"],
            "status": "synced",
        }
        for e in entities
    ]
    push = client.post(
        "/api/v1/sync/push", headers=headers, json={"acks": acks}
    )
    assert push.status_code == 200
    assert push.json()["accepted"] >= 1


def test_sync_service_count(factory: sessionmaker[Session]) -> None:
    db = factory()
    try:
        n = SyncService(db).count_pending(1)
        assert n >= 0
        assert SyncStatus.PENDING.value == "pending"
    finally:
        db.close()


def test_plugin_registry_lists_core() -> None:
    ids = {p.id for p in plugin_registry.list_plugins()}
    assert "core.sync" in ids
    assert "core.telegram" in ids
