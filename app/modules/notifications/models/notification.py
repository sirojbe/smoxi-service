"""In-app notification ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class InAppNotification(AuditMixin, Base):
    """Desktop notification for staff (Telegram inbound, system events)."""

    __tablename__ = "app_notifications"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="info")
    # telegram | work_order | system
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Optional deep-link payload (e.g. telegram chat_id)
    ref_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
