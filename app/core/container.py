"""Application dependency injection container."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 — register ORM models for metadata
from app.config.settings import Settings, get_settings
from app.database.engine import create_db_engine
from app.database.schema_patches import apply_sqlite_schema_patches
from app.database.session import create_session_factory
from app.database.unit_of_work import UnitOfWork
from app.models.base import Base
from app.services.bootstrap_service import BootstrapService


@dataclass
class ServiceContainer:
    """
    Composition root for runtime services.

    Construct once at application startup and pass to UI/controllers.
    """

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session] = field(repr=False)
    _current_user_id: int | None = field(default=None, repr=False)

    @classmethod
    def create(cls, settings: Settings | None = None) -> ServiceContainer:
        """Build a fully wired container."""
        resolved_settings = settings or get_settings()
        engine = create_db_engine()
        session_factory = create_session_factory(engine)
        container = cls(
            settings=resolved_settings,
            engine=engine,
            session_factory=session_factory,
        )
        container.initialize_database()
        return container

    def initialize_database(self) -> None:
        """Create schema and seed mandatory system records."""
        Base.metadata.create_all(self.engine)
        apply_sqlite_schema_patches(self.engine)
        with self.create_unit_of_work() as uow:
            BootstrapService(uow.session).ensure_system_data()
            uow.commit()

    def create_unit_of_work(self) -> UnitOfWork:
        """Return a new UnitOfWork bound to this container."""
        return UnitOfWork(self.session_factory)

    def create_session(self) -> Session:
        """Return a new standalone session (caller must close)."""
        return self.session_factory()

    @property
    def current_user_id(self) -> int | None:
        """Active authenticated user id for audit columns."""
        return self._current_user_id

    def set_current_user(self, user_id: int | None) -> None:
        """Set the active user for the current desktop session."""
        self._current_user_id = user_id

    def shutdown(self) -> None:
        """Dispose database engine resources."""
        self.engine.dispose()
