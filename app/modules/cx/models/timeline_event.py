"""CX timeline ORM model — append-only."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base
from app.modules.cx.models.events import VISIBILITY_STAFF


class WorkOrderTimelineEvent(AuditMixin, Base):
    """Append-only repair timeline event (CX Feature 6 / CX-A)."""

    __tablename__ = "work_order_timeline_events"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, index=True
    )
    event_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default=VISIBILITY_STAFF
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
