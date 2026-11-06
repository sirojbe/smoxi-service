"""Staff Telegram whitelist tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.settings.services.settings_service import (
    CompanyUpdateSchema,
    SettingsService,
)
from app.services.bootstrap_service import BootstrapService
from app.telegram.runtime_status import set_tunnel_reachable, set_tunnel_status
from app.telegram.staff_access import is_staff_chat_allowed, parse_staff_chat_ids
from app.telegram.staff_bot import (
    customer_portal_url,
    customer_web_app_keyboard,
    staff_web_app_keyboard,
    sync_chat_menu_button,
    sync_staff_menu_button,
)


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


def test_parse_staff_chat_ids() -> None:
    assert parse_staff_chat_ids("12646845,64665666") == ["12646845", "64665666"]
    assert parse_staff_chat_ids("12646845, 64665666 ; 999") == [
        "12646845",
        "64665666",
        "999",
    ]
    assert is_staff_chat_allowed("12646845,64665666", "12646845")
    assert not is_staff_chat_allowed("12646845,64665666", "111")
    assert not is_staff_chat_allowed("", "12646845")


def test_resolve_staff_only_whitelisted(db_session: Session) -> None:
    service = SettingsService(db_session)
    company = service.get_company(1)
    payload = CompanyUpdateSchema(
        name=company.name,
        phone=company.phone,
        email=company.email,
        address=company.address,
        tax_id=company.tax_id,
        telegram_bot_token=company.telegram_bot_token,
        telegram_bot_username=company.telegram_bot_username,
        telegram_staff_chat_ids="12646845,64665666",
    )
    service.update_company(1, payload, actor_id=1)
    db_session.commit()

    allowed = service.resolve_staff_user(1, "12646845")
    assert allowed is not None
    assert allowed.username == "1"

    other = service.resolve_staff_user(1, "99999999")
    assert other is None


def test_staff_link_requires_whitelist(db_session: Session) -> None:
    service = SettingsService(db_session)
    company = service.get_company(1)
    service.update_company(
        1,
        CompanyUpdateSchema(
            name=company.name,
            telegram_staff_chat_ids="12646845",
        ),
        actor_id=1,
    )
    db_session.commit()
    user = service.link_staff_telegram(1, username="1", chat_id="12646845")
    assert user.telegram_chat_id == "12646845"
    try:
        service.link_staff_telegram(1, username="1", chat_id="999")
        raise AssertionError("non-whitelist should fail")
    except ValidationError:
        pass


def test_customer_portal_url_and_keyboards(db_session: Session) -> None:
    company = SettingsService(db_session).get_company(1)
    company.telegram_mini_app_url = "https://example.trycloudflare.com/"
    assert customer_portal_url(company) == "https://example.trycloudflare.com/customer/"
    assert (
        staff_web_app_keyboard("https://example.trycloudflare.com")["keyboard"][0][0]["web_app"]["url"]
        == "https://example.trycloudflare.com"
    )
    assert (
        customer_web_app_keyboard("https://example.trycloudflare.com/customer/")["keyboard"][0][0]["web_app"]["url"]
        == "https://example.trycloudflare.com/customer/"
    )


def test_sync_staff_menu_button_uses_customer_portal(db_session: Session) -> None:
    company = SettingsService(db_session).get_company(1)
    company.telegram_mini_app_url = "https://example.trycloudflare.com"

    class FakeClient:
        def __init__(self) -> None:
            self.called: tuple[str, str] | None = None
            self.cleared = False

        def set_chat_menu_button(self, *, text: str = "SMOXI", web_app_url: str, chat_id=None):
            self.called = (text, web_app_url)
            return {"ok": True}

        def clear_chat_menu_button(self, *, chat_id=None):
            self.cleared = True
            return {"ok": True}

    client = FakeClient()
    set_tunnel_status("ok", "https://example.trycloudflare.com")
    set_tunnel_reachable(True)
    sync_staff_menu_button(client, company)  # type: ignore[arg-type]
    assert client.called == ("Kabinet", "https://example.trycloudflare.com/customer/")
    assert not client.cleared


def test_sync_chat_menu_button_uses_role_specific_url(db_session: Session) -> None:
    company = SettingsService(db_session).get_company(1)
    company.telegram_mini_app_url = "https://example.trycloudflare.com"

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str | None, str | None, str | None]] = []

        def set_chat_menu_button(self, *, text: str = "SMOXI", web_app_url: str, chat_id=None):
            self.calls.append((str(chat_id) if chat_id is not None else None, text, web_app_url))
            return {"ok": True}

        def clear_chat_menu_button(self, *, chat_id=None):
            self.calls.append((str(chat_id) if chat_id is not None else None, None, None))
            return {"ok": True}

    client = FakeClient()
    set_tunnel_status("ok", "https://example.trycloudflare.com")
    set_tunnel_reachable(True)
    sync_chat_menu_button(client, company, chat_id="111", is_staff=True)  # type: ignore[arg-type]
    sync_chat_menu_button(client, company, chat_id="222", is_staff=False)  # type: ignore[arg-type]
    assert client.calls[0] == ("111", "SMOXI", "https://example.trycloudflare.com")
    assert client.calls[1] == ("222", "Kabinet", "https://example.trycloudflare.com/customer/")


def test_sync_staff_menu_button_clears_when_offline(db_session: Session) -> None:
    company = SettingsService(db_session).get_company(1)
    company.telegram_mini_app_url = "https://example.trycloudflare.com"

    class FakeClient:
        def __init__(self) -> None:
            self.cleared = False

        def set_chat_menu_button(self, *, text: str = "SMOXI", web_app_url: str, chat_id=None):
            raise AssertionError("offline holatda menu o'rnatilmasligi kerak")

        def clear_chat_menu_button(self, *, chat_id=None):
            self.cleared = True
            return {"ok": True}

    client = FakeClient()
    set_tunnel_status("fail", detail="offline")
    set_tunnel_reachable(False)
    sync_staff_menu_button(client, company)  # type: ignore[arg-type]
    assert client.cleared
