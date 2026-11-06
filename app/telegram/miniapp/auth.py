"""Telegram WebApp initData validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


@dataclass(frozen=True, slots=True)
class WebAppUser:
    """Authenticated Telegram WebApp user."""

    id: str
    first_name: str
    username: str | None


class InitDataError(Exception):
    """initData missing, expired, or signature invalid."""


def parse_and_validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
) -> WebAppUser:
    """Validate Telegram WebApp initData and return the user.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not bot_token:
        raise InitDataError("initData yoki bot token yoʻq.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash yoʻq.")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise InitDataError("Imzo notoʻgʻri.")

    auth_date_raw = pairs.get("auth_date")
    if auth_date_raw and auth_date_raw.isdigit():
        age = int(time.time()) - int(auth_date_raw)
        if age > max_age_seconds:
            raise InitDataError("initData muddati tugagan.")

    user_raw = pairs.get("user")
    if not user_raw:
        raise InitDataError("user yoʻq.")
    try:
        user_obj = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("user JSON notoʻgʻri.") from exc
    user_id = user_obj.get("id")
    if user_id is None:
        raise InitDataError("user.id yoʻq.")
    return WebAppUser(
        id=str(user_id),
        first_name=str(user_obj.get("first_name") or ""),
        username=user_obj.get("username"),
    )
