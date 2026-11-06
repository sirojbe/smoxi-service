"""Staff Mini App auth and API tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.settings.services.settings_service import (
    CompanyUpdateSchema,
    SettingsService,
)
from app.services.bootstrap_service import BootstrapService
from app.telegram.miniapp.app import create_miniapp
from app.telegram.miniapp.auth import InitDataError, parse_and_validate_init_data


def _sign_init_data(bot_token: str, user_id: int = 654114332) -> str:
    user = json.dumps(
        {"id": user_id, "first_name": "Test", "username": "tester"},
        separators=(",", ":"),
    )
    pairs = {
        "auth_date": str(int(time.time())),
        "query_id": "AAE",
        "user": user,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = digest
    return urlencode(pairs)


def test_parse_init_data_ok() -> None:
    token = "123456:ABC-DEF"
    raw = _sign_init_data(token, user_id=42)
    user = parse_and_validate_init_data(raw, token)
    assert user.id == "42"
    assert user.first_name == "Test"


def test_parse_init_data_bad_hash() -> None:
    token = "123456:ABC-DEF"
    raw = _sign_init_data(token) + "x"
    with pytest.raises(InitDataError):
        parse_and_validate_init_data(raw, token)


@pytest.fixture()
def db_engine():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine) -> Session:
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = factory()
    BootstrapService(session).ensure_system_data()
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def mini_client(db_engine, db_session: Session) -> TestClient:
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    class FakeContainer:
        def create_session(self) -> Session:
            return factory()

    token = "999:TESTTOKEN"
    service = SettingsService(db_session)
    company = service.get_company(1)
    service.update_company(
        1,
        CompanyUpdateSchema(
            name=company.name,
            telegram_bot_token=token,
            telegram_staff_chat_ids="654114332",
            telegram_mini_app_url="https://example.trycloudflare.com",
        ),
        actor_id=1,
    )
    db_session.commit()

    app = create_miniapp(FakeContainer(), company_id=1)  # type: ignore[arg-type]
    return TestClient(app)


def test_api_me_forbidden_without_header(mini_client: TestClient) -> None:
    res = mini_client.get("/api/me")
    assert res.status_code == 401


def test_api_me_forbidden_non_staff(mini_client: TestClient) -> None:
    token = "999:TESTTOKEN"
    init = _sign_init_data(token, user_id=111)
    res = mini_client.post(
        "/api/auth/telegram",
        json={"init_data": init},
    )
    assert res.status_code == 403


def test_api_me_ok_for_staff(mini_client: TestClient) -> None:
    token = "999:TESTTOKEN"
    init = _sign_init_data(token, user_id=654114332)
    auth = mini_client.post("/api/auth/telegram", json={"init_data": init})
    assert auth.status_code == 200, auth.text
    bearer = auth.json()["token"]
    res = mini_client.get("/api/me", headers={"Authorization": f"Bearer {bearer}"})
    assert res.status_code == 200
    body = res.json()
    assert "company" in body
    assert body["user"]["username"] == "1"


def test_api_auth_staff_login(mini_client: TestClient, db_session: Session) -> None:
    res = mini_client.post(
        "/api/auth/staff",
        json={"chat_id": "654114332"},
    )
    assert res.status_code == 200, res.text
    bearer = res.json()["token"]
    me = mini_client.get("/api/me", headers={"Authorization": f"Bearer {bearer}"})
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "1"


def test_health(mini_client: TestClient) -> None:
    assert mini_client.get("/api/health").json()["status"] == "ok"


def _staff_headers(token: str = "999:TESTTOKEN") -> dict[str, str]:
    return {"X-Telegram-Init-Data": _sign_init_data(token, user_id=654114332)}


def test_api_intake_creates_work_order(mini_client: TestClient) -> None:
    res = mini_client.post(
        "/api/intake",
        headers=_staff_headers(),
        json={
            "phone": "+998901112233",
            "display_name": "Test Mijoz",
            "device_brand": "Apple",
            "device_model": "iPhone 13",
            "problem_description": "Ekran sindi",
            "estimated_cost": 250000,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ok"
    assert body["number"].startswith("WO-")
    assert body["customer"] == "Test Mijoz"


def test_api_inventory_create_and_adjust(mini_client: TestClient) -> None:
    created = mini_client.post(
        "/api/inventory",
        headers=_staff_headers(),
        json={
            "sku": "SCR-IP13",
            "name": "iPhone 13 ekran",
            "quantity_on_hand": 5,
            "min_quantity": 2,
            "sale_price": 450000,
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["id"]

    listed = mini_client.get("/api/inventory", headers=_staff_headers())
    assert listed.status_code == 200
    assert any(i["sku"] == "SCR-IP13" for i in listed.json()["items"])

    adjusted = mini_client.post(
        f"/api/inventory/{item_id}/adjust",
        headers=_staff_headers(),
        json={"movement_type": "out", "quantity": 2, "reason": "test"},
    )
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()["quantity_on_hand"] == 3

    set_qty = mini_client.post(
        f"/api/inventory/{item_id}/adjust",
        headers=_staff_headers(),
        json={"movement_type": "adjust", "quantity": 10, "reason": "count"},
    )
    assert set_qty.status_code == 200
    assert set_qty.json()["quantity_on_hand"] == 10
