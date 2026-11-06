"""Phone normalization and Telegram auto-link helpers."""

from __future__ import annotations

from app.core.phone import (
    bot_deep_link,
    normalize_phone,
    phone_lookup_variants,
    start_payload_for_phone,
)


def test_normalize_uz_phone() -> None:
    assert normalize_phone("901234567") == "+998901234567"
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"
    assert normalize_phone("998901234567") == "+998901234567"


def test_phone_variants_include_local() -> None:
    variants = phone_lookup_variants("90 123-45-67")
    assert "+998901234567" in variants
    assert "901234567" in variants


def test_bot_deep_link() -> None:
    link = bot_deep_link("@smoxi_bot", start_payload_for_phone("+998901234567"))
    assert link == "https://t.me/smoxi_bot?start=p998901234567"


def test_bot_deep_link_strips_full_url() -> None:
    link = bot_deep_link("https://t.me/SMPhonestore_bot", "w4")
    assert link == "https://t.me/SMPhonestore_bot?start=w4"
    link2 = bot_deep_link("t.me/SMPhonestore_bot?start=old", "w5")
    assert link2 == "https://t.me/SMPhonestore_bot?start=w5"
