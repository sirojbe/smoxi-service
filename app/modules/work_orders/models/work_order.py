"""Work order ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import AuditMixin, Base
from app.modules.work_orders.models.status import WorkOrderPriority, WorkOrderStatus


class WorkOrder(AuditMixin, Base):
    """Service work order (repair / maintenance job)."""

    __tablename__ = "work_orders"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=WorkOrderStatus.RECEIVED.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WorkOrderPriority.NORMAL.value,
    )
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    work_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parts_cost_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parts_sale_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expense_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    technician_id: Mapped[int | None] = mapped_column(
        ForeignKey("technicians.id"),
        nullable=True,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)

    status_history: Mapped[list[WorkOrderStatusHistory]] = relationship(
        "WorkOrderStatusHistory",
        back_populates="work_order",
        order_by="WorkOrderStatusHistory.changed_at",
    )
    parts: Mapped[list[WorkOrderPart]] = relationship(
        "WorkOrderPart",
        back_populates="work_order",
        cascade="all, delete-orphan",
    )


class WorkOrderPart(Base):
    """Part / material used on a work order (cost = expense, sale = customer charge)."""

    __tablename__ = "work_order_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_items.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_sale: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    work_order: Mapped[WorkOrder] = relationship("WorkOrder", back_populates="parts")


class WorkOrderStatusHistory(Base):
    """Immutable status change history for a work order."""

    __tablename__ = "work_order_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    work_order: Mapped[WorkOrder] = relationship("WorkOrder", back_populates="status_history")
