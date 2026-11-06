"""Telegram message repository."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from app.modules.telegram.models.message import TelegramMessage
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class TelegramThreadSummary:
    """One conversation row for the inbox list."""

    chat_id: str
    customer_id: int | None
    last_body: str
    last_at: object
    unread_count: int


class TelegramMessageRepository(BaseRepository[TelegramMessage]):
    """Persistence for telegram_messages."""

    model = TelegramMessage

    def list_for_chat(
        self,
        company_id: int,
        chat_id: str,
        *,
        limit: int = 200,
    ) -> list[TelegramMessage]:
        stmt = (
            self._base_query()
            .where(
                TelegramMessage.company_id == company_id,
                TelegramMessage.chat_id == str(chat_id),
            )
            .order_by(TelegramMessage.created_at.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def list_threads(self, company_id: int, *, limit: int = 100) -> list[TelegramThreadSummary]:
        """Return conversations ordered by latest message."""
        # Distinct chat_ids with latest message via subquery-friendly approach.
        stmt = (
            self._base_query()
            .where(TelegramMessage.company_id == company_id)
            .order_by(TelegramMessage.created_at.desc())
            .limit(2000)
        )
        rows = list(self._session.scalars(stmt))
        by_chat: dict[str, list[TelegramMessage]] = {}
        for row in rows:
            by_chat.setdefault(row.chat_id, []).append(row)

        summaries: list[TelegramThreadSummary] = []
        for chat_id, messages in by_chat.items():
            latest = messages[0]
            unread = sum(
                1
                for m in messages
                if m.direction == "inbound" and not m.is_read
            )
            summaries.append(
                TelegramThreadSummary(
                    chat_id=chat_id,
                    customer_id=latest.customer_id,
                    last_body=latest.body,
                    last_at=latest.created_at,
                    unread_count=unread,
                )
            )
        summaries.sort(key=lambda s: s.last_at or 0, reverse=True)
        return summaries[:limit]

    def mark_chat_read(self, company_id: int, chat_id: str) -> int:
        stmt = self._base_query().where(
            TelegramMessage.company_id == company_id,
            TelegramMessage.chat_id == str(chat_id),
            TelegramMessage.direction == "inbound",
            TelegramMessage.is_read.is_(False),
        )
        count = 0
        for row in self._session.scalars(stmt):
            row.is_read = True
            count += 1
        if count:
            self._session.flush()
        return count

    def count_unread(self, company_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(TelegramMessage)
            .where(
                TelegramMessage.company_id == company_id,
                TelegramMessage.deleted_at.is_(None),
                TelegramMessage.direction == "inbound",
                TelegramMessage.is_read.is_(False),
            )
        )
        return int(self._session.scalar(stmt) or 0)
