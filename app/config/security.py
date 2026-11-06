"""
Security configuration placeholders for SMOXI Service.

Authentication, authorization, token lifetimes, and password policies will be
implemented in later phases. This module only defines starter settings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.settings import PROJECT_ROOT


class SecuritySettings(BaseSettings):
    """
    Security-related configuration.

    Do not hard-code production secrets. Override via environment variables
    prefixed with ``SMOXI_SECURITY_``.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="SMOXI_SECURITY_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Cryptography / signing ---
    secret_key: str = Field(
        default="change-me-in-production",
        description="Primary secret for signing tokens and encrypting sensitive payloads.",
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT (or similar) signing algorithm placeholder.",
    )

    # --- Token lifetimes (seconds) — placeholders for future auth module ---
    access_token_expire_seconds: int = Field(
        default=3600,
        description="Access token lifetime in seconds.",
    )
    refresh_token_expire_seconds: int = Field(
        default=60 * 60 * 24 * 7,
        description="Refresh token lifetime in seconds.",
    )

    # --- Password policy ---
    password_min_length: int = Field(
        default=4,
        description="Minimum password length (SMB-friendly; raise in production via env).",
    )
    password_require_special: bool = Field(
        default=False,
        description="Require at least one special character in passwords.",
    )


@lru_cache(maxsize=1)
def get_security_settings() -> SecuritySettings:
    """Return a cached SecuritySettings instance."""
    return SecuritySettings()
