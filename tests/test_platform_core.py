"""Platform core tests."""

from __future__ import annotations

from app.core.time import utc_now
from app.security.password import hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Smoxi@2026!")
    assert verify_password("Smoxi@2026!", hashed)
    assert not verify_password("wrong", hashed)


def test_utc_now_is_timezone_aware() -> None:
    assert utc_now().tzinfo is not None
