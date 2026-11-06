"""Tests for Mini App tunnel strategy resolution."""

from __future__ import annotations

from app.config.settings import Settings
from app.telegram.miniapp.tunnel_plan import resolve_tunnel_plan


def test_auto_quick_when_empty() -> None:
    plan = resolve_tunnel_plan(
        company_public_url=None,
        company_tunnel_token=None,
        settings=Settings(
            miniapp_public_url="",
            cloudflare_tunnel_token="",
            miniapp_tunnel_mode="auto",
        ),
    )
    assert plan.mode == "quick"


def test_auto_named_when_token_and_url() -> None:
    plan = resolve_tunnel_plan(
        company_public_url="https://staff.example.com",
        company_tunnel_token=None,
        settings=Settings(
            miniapp_public_url="",
            cloudflare_tunnel_token="tok_abc",
            miniapp_tunnel_mode="auto",
        ),
    )
    assert plan.mode == "named"
    assert plan.public_url == "https://staff.example.com"
    assert plan.tunnel_token == "tok_abc"


def test_auto_external_for_fixed_url_without_token() -> None:
    plan = resolve_tunnel_plan(
        company_public_url="https://staff.example.com",
        company_tunnel_token=None,
        settings=Settings(
            miniapp_public_url="",
            cloudflare_tunnel_token="",
            miniapp_tunnel_mode="auto",
        ),
    )
    assert plan.mode == "external"
    assert plan.public_url == "https://staff.example.com"


def test_auto_named_decrypts_company_tunnel_token(monkeypatch) -> None:
    monkeypatch.setenv("SMOXI_SECURITY_SECRET_KEY", "unit-test-secret-key-1234567890")
    from app.config.security import get_security_settings
    from app.security import secrets as secrets_mod
    from app.security.secrets import encrypt_secret

    get_security_settings.cache_clear()
    secrets_mod._fernet_for.cache_clear()
    stored = encrypt_secret("tok_from_company")
    plan = resolve_tunnel_plan(
        company_public_url="https://staff.example.com",
        company_tunnel_token=stored,
        settings=Settings(
            miniapp_public_url="",
            cloudflare_tunnel_token="",
            miniapp_tunnel_mode="auto",
        ),
    )
    assert plan.mode == "named"
    assert plan.tunnel_token == "tok_from_company"


def test_trycloudflare_url_falls_back_to_quick() -> None:
    plan = resolve_tunnel_plan(
        company_public_url="https://abc.trycloudflare.com",
        company_tunnel_token=None,
        settings=Settings(
            miniapp_public_url="",
            cloudflare_tunnel_token="",
            miniapp_tunnel_mode="auto",
        ),
    )
    assert plan.mode == "quick"
