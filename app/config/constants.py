"""
Application-wide constants for SMOXI Service.

Use this module for immutable values shared across layers.
Avoid putting environment-specific configuration here — use settings instead.
"""

from __future__ import annotations

from typing import Final

# --- Product identity ---
APP_NAME: Final[str] = "SMOXI Service"
APP_SLUG: Final[str] = "smoxi-service"
ORGANIZATION_NAME: Final[str] = "SMOXI"
ORGANIZATION_DOMAIN: Final[str] = "smoxi.local"

# --- Localization defaults ---
DEFAULT_LOCALE: Final[str] = "uz_UZ"
SUPPORTED_LOCALES: Final[tuple[str, ...]] = (
    "uz_UZ",
    "ru_RU",
    "en_US",
    "de_DE",
)

# --- Desktop / Qt ---
QT_ORGANIZATION: Final[str] = ORGANIZATION_NAME
QT_APPLICATION: Final[str] = APP_NAME

# --- API (future FastAPI surface) ---
API_V1_PREFIX: Final[str] = "/api/v1"

# --- Date / time display formats (UI layer) ---
DATE_FORMAT: Final[str] = "yyyy-MM-dd"
DATETIME_FORMAT: Final[str] = "yyyy-MM-dd HH:mm:ss"

# --- Reception defaults ---
DEFAULT_PHONE_PREFIX: Final[str] = "+998"
DEFAULT_SERVICE_PRICE: Final[int] = 10_000
