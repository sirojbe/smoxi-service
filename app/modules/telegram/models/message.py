"""Telegram chat message ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class TelegramMessage(AuditMixin, Base):
    """Persisted inbound/outbound Telegram chat message."""

    __tablename__ = "telegram_messages"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"),
        nullable=True,
        index=True,
    )
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_orders.id"),
        nullable=True,
        index=True,
    )
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound | outbound
    body: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_auto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
