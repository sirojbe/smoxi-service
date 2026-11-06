"""SQLAlchemy declarative base and shared model mixins."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.enums import SyncStatus
from app.core.time import utc_now


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class AuditMixin:
    """
    Mandatory audit and soft-delete columns for business tables.

    Matches Engineering Standards and Business Analysis requirements.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SyncStatus.PENDING.value,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True when the row is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self, *, actor_id: int | None = None) -> None:
        """Mark the entity as soft-deleted."""
        self.deleted_at = utc_now()
        self.updated_by = actor_id
        self.version += 1
        self.sync_status = SyncStatus.PENDING.value

    def restore(self, *, actor_id: int | None = None) -> None:
        """Restore a soft-deleted entity."""
        self.deleted_at = None
        self.updated_by = actor_id
        self.version += 1
        self.sync_status = SyncStatus.PENDING.value


@event.listens_for(AuditMixin, "before_update", propagate=True)
def _increment_version_on_update(mapper: Any, connection: Any, target: AuditMixin) -> None:
    """Bump optimistic-lock version on every update."""
    target.version += 1
    target.updated_at = utc_now()
    if target.sync_status == SyncStatus.SYNCED.value:
        target.sync_status = SyncStatus.PENDING.value
