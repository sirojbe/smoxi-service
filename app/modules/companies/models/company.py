"""Company ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.users.models.user import User

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Company(AuditMixin, Base):
    """Legal entity / brand operating service centers."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_staff_pin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    telegram_staff_chat_ids: Mapped[str | None] = mapped_column(String(512), nullable=True)
    telegram_mini_app_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cloudflare_tunnel_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list[User]] = relationship("User", back_populates="company")
