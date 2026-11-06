"""SQLAlchemy engine factory."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url

from app.config.database import DatabaseSettings, get_database_settings


def create_db_engine(settings: DatabaseSettings | None = None) -> Engine:
    """
    Create a SQLAlchemy engine for the configured backend.

    SQLite is configured for desktop use (WAL, foreign keys, thread safety).
    """
    db_settings = settings or get_database_settings()
    url = db_settings.url
    echo = db_settings.sqlite_echo if db_settings.backend == "sqlite" else db_settings.postgres_echo

    connect_args: dict[str, object] = {}
    if db_settings.backend == "sqlite":
        db_settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}

    if db_settings.backend == "postgresql":
        engine = create_engine(
            url,
            echo=echo,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            pool_timeout=db_settings.pool_timeout,
            pool_pre_ping=True,
        )
    else:
        engine = create_engine(
            url,
            echo=echo,
            connect_args=connect_args,
        )

    if make_url(url).get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine
