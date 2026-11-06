"""Unit tests for at-rest secret encryption."""

from __future__ import annotations

from app.security.secrets import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_roundtrip(monkeypatch) -> None:
    monkeypatch.setenv("SMOXI_SECURITY_SECRET_KEY", "unit-test-secret-key-1234567890")
    from app.config.security import get_security_settings

    get_security_settings.cache_clear()
    from app.security import secrets as secrets_mod

    secrets_mod._fernet_for.cache_clear()

    stored = encrypt_secret("123456:ABC-DEF")
    assert stored is not None
    assert stored.startswith("smoxi1:")
    assert decrypt_secret(stored) == "123456:ABC-DEF"


def test_legacy_plaintext_passthrough() -> None:
    assert decrypt_secret("plain-token") == "plain-token"
    assert encrypt_secret(None) is None
