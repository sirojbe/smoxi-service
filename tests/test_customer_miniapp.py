"""Customer Mini App API smoke tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.services.bootstrap_service import BootstrapService
from app.telegram.customer_miniapp.app import create_customer_miniapp


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


def test_customer_health_endpoint(factory: sessionmaker[Session]) -> None:
    app = create_customer_miniapp(_FakeContainer(factory), company_id=1)  # type: ignore[arg-type]
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["portal"] == "customer"


def test_customer_me_requires_auth(factory: sessionmaker[Session]) -> None:
    app = create_customer_miniapp(_FakeContainer(factory), company_id=1)  # type: ignore[arg-type]
    client = TestClient(app)
    res = client.get("/api/me")
    assert res.status_code in {401, 503}
