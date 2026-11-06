"""At-rest encryption helpers for sensitive company settings."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config.logging import get_logger
from app.config.security import get_security_settings

logger = get_logger("security.secrets")

_PREFIX = "smoxi1:"
_DEFAULT_SECRET = "change-me-in-production"


def is_default_secret(secret: str | None) -> bool:
    """Return True when the configured secret is still the unsafe default."""
    return not secret or secret.strip() == _DEFAULT_SECRET


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=4)
def _fernet_for(secret: str) -> Fernet:
    return Fernet(_derive_fernet_key(secret))


def encrypt_secret(plaintext: str | None) -> str | None:
    """
    Encrypt a secret for database storage.

    Plaintext that is already encrypted (starts with ``smoxi1:``) is returned as-is.
    Empty values become ``None``.
    """
    if plaintext is None:
        return None
    value = plaintext.strip()
    if not value:
        return None
    if value.startswith(_PREFIX):
        return value
    settings = get_security_settings()
    token = _fernet_for(settings.secret_key).encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_PREFIX}{token}"


def decrypt_secret(stored: str | None) -> str:
    """
    Decrypt a stored secret.

    Legacy plaintext values (no prefix) are returned unchanged so existing installs
    keep working until the next save re-encrypts them.
    """
    if not stored:
        return ""
    value = stored.strip()
    if not value.startswith(_PREFIX):
        return value
    payload = value[len(_PREFIX) :]
    settings = get_security_settings()
    try:
        return _fernet_for(settings.secret_key).decrypt(payload.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        logger.error("Sirni ochib boʻlmadi: {}", exc)
        return ""


def company_bot_token(company: object) -> str:
    """Return decrypted Telegram bot token from a company-like object."""
    raw = getattr(company, "telegram_bot_token", None)
    return decrypt_secret(raw if isinstance(raw, str) else None)
