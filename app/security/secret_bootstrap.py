"""Startup checks and local secret generation for production readiness."""

from __future__ import annotations

import os
import secrets

from app.config.logging import get_logger
from app.config.security import get_security_settings
from app.config.settings import PROJECT_ROOT, get_settings
from app.security.secrets import is_default_secret

logger = get_logger("security.bootstrap")

LOCAL_SECRET_FILE = PROJECT_ROOT / ".smoxi_secret_key"


def ensure_runtime_secrets() -> None:
    """
    Refuse default secrets in production; auto-mint a local key in development.

    Call once during application bootstrap after logging is configured.
    """
    settings = get_settings()
    security = get_security_settings()

    if settings.environment == "production":
        if is_default_secret(security.secret_key) or is_default_secret(settings.secret_key):
            raise RuntimeError(
                "Production muhitida default SECRET_KEY taqiqlanadi. "
                "`.env` faylida SMOXI_SECURITY_SECRET_KEY va SMOXI_SECRET_KEY ni "
                "mustahkam qiymat bilan almashtiring."
            )
        return

    if not is_default_secret(security.secret_key):
        return

    minted = _load_or_create_local_secret()
    os.environ["SMOXI_SECURITY_SECRET_KEY"] = minted
    if is_default_secret(settings.secret_key):
        os.environ["SMOXI_SECRET_KEY"] = minted
    get_security_settings.cache_clear()
    get_settings.cache_clear()

    logger.warning(
        "Default SECRET_KEY o‘rniga mahalliy kalit ishlatilmoqda ({path}). "
        "Productionda albatta environment orqali bering.",
        path=str(LOCAL_SECRET_FILE),
    )


def _load_or_create_local_secret() -> str:
    if LOCAL_SECRET_FILE.exists():
        value = LOCAL_SECRET_FILE.read_text(encoding="utf-8").strip()
        if value and not is_default_secret(value):
            return value
    value = secrets.token_urlsafe(48)
    LOCAL_SECRET_FILE.write_text(value + "\n", encoding="utf-8")
    try:
        LOCAL_SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return value
