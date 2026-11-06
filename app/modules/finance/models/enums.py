"""Finance domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Invoice lifecycle statuses."""

    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentMethod(StrEnum):
    """Supported payment methods."""

    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    MIXED = "mixed"


class CashSessionStatus(StrEnum):
    """Cash register session status."""

    OPEN = "open"
    CLOSED = "closed"


INVOICE_STATUS_LABELS_UZ: dict[InvoiceStatus, str] = {
    InvoiceStatus.DRAFT: "Qoralama",
    InvoiceStatus.ISSUED: "Chiqarilgan",
    InvoiceStatus.PARTIALLY_PAID: "Qisman toʻlangan",
    InvoiceStatus.PAID: "Toʻlangan",
    InvoiceStatus.VOID: "Bekor",
}

PAYMENT_METHOD_LABELS_UZ: dict[PaymentMethod, str] = {
    PaymentMethod.CASH: "Naqd",
    PaymentMethod.CARD: "Karta",
    PaymentMethod.TRANSFER: "Oʻtkazma",
    PaymentMethod.MIXED: "Aralash",
}


def invoice_status_label(status: str | InvoiceStatus) -> str:
    try:
        return INVOICE_STATUS_LABELS_UZ[InvoiceStatus(status)]
    except ValueError:
        return str(status)


def payment_method_label(method: str | PaymentMethod) -> str:
    try:
        return PAYMENT_METHOD_LABELS_UZ[PaymentMethod(method)]
    except ValueError:
        return str(method)
