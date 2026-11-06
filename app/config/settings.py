"""
Application settings powered by Pydantic Settings.

This module defines environment-driven configuration for SMOXI Service.
Business-specific settings should be added in later phases.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: SMOXI-Service/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables and optional `.env` files.
    Keep secrets out of source control; use environment injection instead.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="SMOXI_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="SMOXI Service", description="Product display name.")
    app_version: str = Field(default="1.13.0", description="Semantic application version.")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Runtime environment identifier.",
    )
    debug: bool = Field(default=True, description="Enable verbose diagnostics in development.")

    # --- Paths ---
    project_root: Path = Field(default=PROJECT_ROOT, description="Absolute project root path.")
    logs_dir: Path = Field(
        default=PROJECT_ROOT / "logs",
        description="Directory for application log files.",
    )
    uploads_dir: Path = Field(
        default=PROJECT_ROOT / "uploads",
        description="Directory for user-uploaded files.",
    )
    backups_dir: Path = Field(
        default=PROJECT_ROOT / "backups",
        description="Directory for database and system backups.",
    )

    # --- Database (connection details live in database.py) ---
    database_backend: Literal["sqlite", "postgresql"] = Field(
        default="sqlite",
        description="Active persistence backend for the current runtime.",
    )

    # --- Security placeholders (details in security.py) ---
    secret_key: str = Field(
        default="change-me-in-production",
        description="Application secret used for signing and encryption.",
    )

    # --- Mini App / Cloudflare tunnel ---
    miniapp_public_url: str = Field(
        default="",
        description="Fixed HTTPS URL for the staff Mini App (named tunnel or custom domain).",
    )
    cloudflare_tunnel_token: str = Field(
        default="",
        description="Cloudflare named tunnel token (tunnel run --token). Empty = quick tunnel.",
    )
    miniapp_tunnel_mode: Literal["auto", "named", "quick", "external"] = Field(
        default="auto",
        description=(
            "auto: named if token+URL, external if fixed URL only, else quick trycloudflare; "
            "named/quick/external force that strategy."
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Prefer this factory over constructing Settings repeatedly so configuration
    remains consistent across the process lifetime.
    """
    return Settings()
