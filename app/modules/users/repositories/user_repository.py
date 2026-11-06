"""User repository."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.modules.users.models.user import Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Persistence operations for users."""

    model = User

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_username(self, company_id: int, username: str) -> User | None:
        """Return a user by company and username."""
        stmt = (
            self._base_query()
            .where(User.company_id == company_id, User.username == username)
            .options(joinedload(User.role).joinedload(Role.permissions))
        )
        return self._session.scalar(stmt)

    def get_by_telegram_chat_id(self, company_id: int, chat_id: str) -> User | None:
        """Return staff user linked to a Telegram chat."""
        stmt = (
            self._base_query()
            .where(
                User.company_id == company_id,
                User.telegram_chat_id == str(chat_id),
                User.is_active.is_(True),
            )
            .options(joinedload(User.role))
        )
        return self._session.scalar(stmt)

    def get_default_staff_actor(self, company_id: int) -> User | None:
        """Return preferred actor for whitelist staff actions (owner/admin first)."""
        stmt = (
            self._base_query()
            .where(User.company_id == company_id, User.is_active.is_(True))
            .options(joinedload(User.role))
            .order_by(User.id)
        )
        users = list(self._session.scalars(stmt).unique())
        if not users:
            return None
        preferred = {"owner", "admin"}
        for user in users:
            code = (user.role.code if user.role else "") or ""
            if code in preferred:
                return user
        return users[0]

    def get_with_role(self, user_id: int) -> User | None:
        """Return a user with role and permissions loaded."""
        stmt = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(joinedload(User.role).joinedload(Role.permissions))
        )
        return self._session.scalar(stmt)

    def count_all(self) -> int:
        """Return total active user count."""
        stmt: Select[tuple[int]] = select(User.id).where(User.deleted_at.is_(None))
        return len(list(self._session.scalars(stmt)))
