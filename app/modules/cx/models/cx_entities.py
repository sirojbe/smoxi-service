"""CX media, signature, intake, warranty, delivery ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.models.base import AuditMixin, Base


class IntakeSnapshot(AuditMixin, Base):
    """Device reception snapshot attached 1:1 to a work order (CX-B)."""

    __tablename__ = "cx_intake_snapshots"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, unique=True, index=True
    )
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_sim: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_memory_card: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    battery_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screen_condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    water_damage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    previous_repairs: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_completion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class MediaAsset(AuditMixin, Base):
    """Photo or video attached to a work order (CX-C)."""

    __tablename__ = "cx_media_assets"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, index=True
    )
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)  # photo | video
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default="before")  # before|after
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CustomerSignature(AuditMixin, Base):
    """Immutable customer signature for intake (CX-B Feature 4)."""

    __tablename__ = "cx_customer_signatures"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, index=True
    )
    signature_path: Mapped[str] = mapped_column(String(500), nullable=False)
    terms_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    employee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ReceiptDocument(AuditMixin, Base):
    """Generated intake PDF archive (CX-B Feature 5)."""

    __tablename__ = "cx_receipt_documents"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, index=True
    )
    doc_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class NotificationDelivery(AuditMixin, Base):
    """Telegram/SMS delivery attempt log (CX-E)."""

    __tablename__ = "cx_notification_deliveries"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_orders.id"), nullable=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # sent|failed|pending
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PartReservation(AuditMixin, Base):
    """Spare part reservation for a work order (CX-F)."""

    __tablename__ = "cx_part_reservations"
    __table_args__ = (
        UniqueConstraint(
            "work_order_id",
            "inventory_item_id",
            name="uq_cx_reservation_wo_item",
        ),
    )

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, index=True
    )
    inventory_item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reserved"
    )  # reserved|consumed|released


class WarrantyCard(AuditMixin, Base):
    """Warranty card issued after delivery (CX-G)."""

    __tablename__ = "cx_warranty_cards"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, unique=True, index=True
    )
    warranty_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parts_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
