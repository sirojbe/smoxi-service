"""Helpers for staff Telegram ID whitelist."""

from __future__ import annotations

import re


def parse_staff_chat_ids(raw: str | None) -> list[str]:
    """Parse comma/space/semicolon separated Telegram chat IDs.

    Examples: ``12646845,64665666`` or ``12646845, 64665666``.
    """
    if not raw:
        return []
    parts = re.split(r"[,;\s]+", raw.strip())
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        cleaned = part.strip().lstrip("+")
        if not cleaned:
            continue
        # Telegram chat ids are digits (optionally leading minus for groups)
        if cleaned.lstrip("-").isdigit() and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def normalize_staff_chat_ids(raw: str | None) -> str | None:
    """Return canonical comma-separated list or None if empty."""
    ids = parse_staff_chat_ids(raw)
    if not ids:
        return None
    return ",".join(ids)


def is_staff_chat_allowed(raw: str | None, chat_id: str) -> bool:
    """True if chat_id is in the company whitelist."""
    allowed = set(parse_staff_chat_ids(raw))
    return bool(allowed) and str(chat_id).strip() in allowed
