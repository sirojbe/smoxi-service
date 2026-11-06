"""Signed staff session tokens for Mini App (Telegram or PIN login)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StaffSession:
    """Decoded Mini App staff session."""

    user_id: int
    company_id: int
    telegram_id: str
    exp: int


class SessionTokenError(Exception):
    """Invalid or expired staff session token."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + pad).encode("ascii"))


def issue_staff_token(
    *,
    secret: str,
    user_id: int,
    company_id: int,
    telegram_id: str,
    ttl_seconds: int = 12 * 3600,
) -> str:
    """Create a signed staff session token."""
    if not secret:
        raise SessionTokenError("Secret yoʻq.")
    payload = {
        "uid": int(user_id),
        "cid": int(company_id),
        "tg": str(telegram_id),
        "exp": int(time.time()) + int(ttl_seconds),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(
        secret.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{sig}"


def parse_staff_token(token: str, *, secret: str, company_id: int) -> StaffSession:
    """Validate signed token and return session claims."""
    if not token or not secret:
        raise SessionTokenError("Token yoʻq.")
    parts = token.strip().split(".")
    if len(parts) != 2:
        raise SessionTokenError("Token formati notoʻgʻri.")
    body, sig = parts
    expected = hmac.new(
        secret.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise SessionTokenError("Token imzosi notoʻgʻri.")
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SessionTokenError("Token oʻqilmadi.") from exc
    try:
        exp = int(payload["exp"])
        uid = int(payload["uid"])
        cid = int(payload["cid"])
        tg = str(payload["tg"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionTokenError("Token maydonlari notoʻgʻri.") from exc
    if cid != company_id:
        raise SessionTokenError("Kompaniya mos emas.")
    if exp < int(time.time()):
        raise SessionTokenError("Sessiya muddati tugagan.")
    return StaffSession(user_id=uid, company_id=cid, telegram_id=tg, exp=exp)
