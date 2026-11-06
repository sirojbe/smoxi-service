"""Unit of Work pattern for transactional consistency."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker


class UnitOfWork:
    """
    Manage a single database transaction boundary.

    Usage::

        with unit_of_work as uow:
            repo.add(entity)
            uow.commit()
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """Return the active SQLAlchemy session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active. Use it as a context manager.")
        return self._session

    def __enter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self.session.rollback()
