"""Phone number helpers shared across modules."""

from __future__ import annotations


def digits_only(value: str) -> str:
    """Return only digits from a phone-like string."""
    return "".join(ch for ch in value if ch.isdigit())


def normalize_phone(value: str) -> str:
    """
    Normalize Uzbekistan-friendly phone to +998XXXXXXXXX when possible.

    Accepts: +99890..., 99890..., 90..., 00998...
    """
    digits = digits_only(value)
    if not digits:
        return value.strip()
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+998{digits[1:]}"
    if len(digits) == 9:
        return f"+998{digits}"
    if value.strip().startswith("+"):
        return f"+{digits}"
    return f"+{digits}" if len(digits) >= 9 else value.strip()


def phone_lookup_variants(value: str) -> list[str]:
    """Return unique phone forms to try when searching the database."""
    raw = value.strip()
    normalized = normalize_phone(raw)
    digits = digits_only(normalized)
    variants = [raw, normalized, digits, f"+{digits}"]
    if digits.startswith("998") and len(digits) == 12:
        variants.append(digits[3:])
        variants.append(f"0{digits[3:]}")
    seen: set[str] = set()
    result: list[str] = []
    for item in variants:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def start_payload_for_phone(phone: str) -> str:
    """Deep-link payload for /start (Telegram allows A-Za-z0-9_)."""
    digits = digits_only(normalize_phone(phone))
    return f"p{digits}"


def start_payload_for_work_order(work_order_id: int) -> str:
    return f"w{work_order_id}"


def normalize_bot_username(bot_username: str | None) -> str | None:
    """
    Normalize bot username from settings.

    Accepts: @name, name, https://t.me/name, t.me/name
    """
    if not bot_username:
        return None
    username = bot_username.strip()
    if not username:
        return None
    username = username.lstrip("@")
    lower = username.lower()
    for prefix in (
        "https://t.me/",
        "http://t.me/",
        "https://telegram.me/",
        "http://telegram.me/",
        "t.me/",
        "telegram.me/",
    ):
        if lower.startswith(prefix):
            username = username[len(prefix) :]
            break
    username = username.split("?")[0].split("/")[0].strip().lstrip("@")
    return username or None


def bot_deep_link(bot_username: str | None, payload: str) -> str | None:
    """Build https://t.me/<bot>?start=<payload>."""
    username = normalize_bot_username(bot_username)
    if not username:
        return None
    return f"https://t.me/{username}?start={payload}"
