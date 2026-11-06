"""
Database configuration for SMOXI Service.

Supports local SQLite (desktop) and cloud PostgreSQL (server/sync) backends.
Engine and session factories will be wired in later phases — no schema creation here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.settings import PROJECT_ROOT


class DatabaseSettings(BaseSettings):
    """
    Persistence-layer settings.

    Keep connection strings and pool tuning here so application code depends on
    abstractions rather than hard-coded URLs.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="SMOXI_DB_",
        case_sensitive=False,
        extra="ignore",
    )

    backend: Literal["sqlite", "postgresql"] = Field(
        default="sqlite",
        description="Selected database backend.",
    )

    # --- SQLite (local desktop) ---
    sqlite_path: Path = Field(
        default=PROJECT_ROOT / "database" / "sqlite" / "smoxi.db",
        description="Path to the local SQLite database file.",
    )
    sqlite_echo: bool = Field(
        default=False,
        description="Echo SQL statements when using SQLite (development aid).",
    )

    # --- PostgreSQL (cloud / multi-user) ---
    postgres_host: str = Field(default="localhost", description="PostgreSQL host.")
    postgres_port: int = Field(default=5432, description="PostgreSQL port.")
    postgres_user: str = Field(default="smoxi", description="PostgreSQL username.")
    postgres_password: str = Field(default="", description="PostgreSQL password.")
    postgres_database: str = Field(default="smoxi_service", description="PostgreSQL database name.")
    postgres_echo: bool = Field(
        default=False,
        description="Echo SQL statements when using PostgreSQL.",
    )

    # --- SQLAlchemy pool (primarily for PostgreSQL) ---
    pool_size: int = Field(default=5, description="Connection pool size.")
    max_overflow: int = Field(default=10, description="Max overflow connections beyond pool_size.")
    pool_timeout: int = Field(default=30, description="Seconds to wait for a free connection.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlite_url(self) -> str:
        """Build a SQLAlchemy-compatible SQLite URL."""
        # Ensure parent directory exists before first connection (later phase).
        return f"sqlite:///{self.sqlite_path.as_posix()}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_url(self) -> str:
        """Build a SQLAlchemy-compatible PostgreSQL URL (psycopg driver)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        """Return the active database URL for the configured backend."""
        if self.backend == "postgresql":
            return self.postgres_url
        return self.sqlite_url


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Return a cached DatabaseSettings instance."""
    return DatabaseSettings()
