"""Generic repository abstractions."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.base import AuditMixin

T = TypeVar("T", bound=AuditMixin)


class BaseRepository(Generic[T]):
    """Base CRUD repository with soft-delete awareness."""

    model: type[T]

    def __init__(self, session: Session) -> None:
        self._session = session

    def _base_query(self, *, include_deleted: bool = False) -> Select[tuple[T]]:
        stmt = select(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, entity_id: int, *, include_deleted: bool = False) -> T | None:
        """Return an entity by primary key or None."""
        stmt = self._base_query(include_deleted=include_deleted).where(self.model.id == entity_id)
        return self._session.scalar(stmt)

    def get_by_uuid(self, entity_uuid: str, *, include_deleted: bool = False) -> T | None:
        """Return an entity by UUID or None."""
        stmt = self._base_query(include_deleted=include_deleted).where(self.model.uuid == entity_uuid)
        return self._session.scalar(stmt)

    def require_by_id(self, entity_id: int) -> T:
        """Return an entity by primary key or raise NotFoundError."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError(
                f"{self.model.__name__} topilmadi (id={entity_id}).",
                entity=self.model.__name__,
            )
        return entity

    def list_all(self, *, include_deleted: bool = False) -> list[T]:
        """Return all entities matching the base query."""
        return list(self._session.scalars(self._base_query(include_deleted=include_deleted)))

    def add(self, entity: T) -> T:
        """Persist a new entity."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def save(self, entity: T) -> T:
        """Flush changes for an existing entity."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def soft_delete(self, entity: T, *, actor_id: int | None = None) -> T:
        """Soft-delete an entity."""
        entity.soft_delete(actor_id=actor_id)
        self._session.flush()
        return entity
