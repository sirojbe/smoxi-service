"""Notification repository."""

from __future__ import annotations

from sqlalchemy import func, select, update

from app.modules.notifications.models.notification import InAppNotification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[InAppNotification]):
    """Persistence for app_notifications."""

    model = InAppNotification

    def list_for_company(
        self,
        company_id: int,
        *,
        unread_only: bool = False,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[InAppNotification]:
        stmt = (
            self._base_query()
            .where(InAppNotification.company_id == company_id)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(InAppNotification.is_read.is_(False))
        if kind and kind not in {"all", ""}:
            stmt = stmt.where(InAppNotification.kind == kind)
        return list(self._session.scalars(stmt))

    def count_unread(self, company_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(InAppNotification)
            .where(
                InAppNotification.company_id == company_id,
                InAppNotification.deleted_at.is_(None),
                InAppNotification.is_read.is_(False),
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def mark_read(self, notification_id: int) -> None:
        row = self.get_by_id(notification_id)
        if row is None:
            return
        row.is_read = True
        self._session.flush()

    def mark_all_read(self, company_id: int) -> int:
        stmt = (
            update(InAppNotification)
            .where(
                InAppNotification.company_id == company_id,
                InAppNotification.deleted_at.is_(None),
                InAppNotification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)
