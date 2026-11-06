"""Purchase order status enumerations."""

from __future__ import annotations

from enum import StrEnum


class PurchaseOrderStatus(StrEnum):
    """Purchase order lifecycle."""

    DRAFT = "draft"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"


PO_STATUS_LABELS_UZ: dict[PurchaseOrderStatus, str] = {
    PurchaseOrderStatus.DRAFT: "Qoralama",
    PurchaseOrderStatus.ORDERED: "Buyurtma berilgan",
    PurchaseOrderStatus.RECEIVED: "Qabul qilingan",
    PurchaseOrderStatus.CANCELLED: "Bekor qilingan",
}


def po_status_label(status: str | PurchaseOrderStatus) -> str:
    try:
        return PO_STATUS_LABELS_UZ[PurchaseOrderStatus(status)]
    except ValueError:
        return str(status)
