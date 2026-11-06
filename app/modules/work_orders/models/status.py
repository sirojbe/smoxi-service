"""Work order status enumerations and transition rules."""

from __future__ import annotations

from enum import StrEnum

from app.core.exceptions import ValidationError


class WorkOrderStatus(StrEnum):
    """Canonical work order statuses (Business Analysis §10)."""

    RECEIVED = "received"
    WAITING_DIAGNOSIS = "waiting_diagnosis"
    DIAGNOSING = "diagnosing"
    WAITING_CUSTOMER_APPROVAL = "waiting_customer_approval"
    APPROVED = "approved"
    WAITING_PARTS = "waiting_parts"
    REPAIRING = "repairing"
    TESTING = "testing"
    QUALITY_CHECK = "quality_check"
    READY = "ready"
    DELIVERED = "delivered"
    WARRANTY = "warranty"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class WorkOrderPriority(StrEnum):
    """Work order priority levels."""

    NORMAL = "normal"
    EXPRESS = "express"
    EMERGENCY = "emergency"


STATUS_LABELS_UZ: dict[WorkOrderStatus, str] = {
    WorkOrderStatus.RECEIVED: "Qabul qilindi",
    WorkOrderStatus.WAITING_DIAGNOSIS: "Diagnostika kutilmoqda",
    WorkOrderStatus.DIAGNOSING: "Diagnostika qilinmoqda",
    WorkOrderStatus.WAITING_CUSTOMER_APPROVAL: "Mijoz roziligi kutilmoqda",
    WorkOrderStatus.APPROVED: "Tasdiqlangan",
    WorkOrderStatus.WAITING_PARTS: "Ehtiyot qism kutilyapti",
    WorkOrderStatus.REPAIRING: "Taʼmirlanmoqda",
    WorkOrderStatus.TESTING: "Sinovdan oʻtkazilmoqda",
    WorkOrderStatus.QUALITY_CHECK: "Sifat nazorati",
    WorkOrderStatus.READY: "Tayyor",
    WorkOrderStatus.DELIVERED: "Topshirildi",
    WorkOrderStatus.WARRANTY: "Kafolatda",
    WorkOrderStatus.CLOSED: "Yopildi",
    WorkOrderStatus.CANCELLED: "Bekor qilindi",
    WorkOrderStatus.REJECTED: "Rad etildi",
    WorkOrderStatus.ARCHIVED: "Arxivlangan",
}

PRIORITY_LABELS_UZ: dict[WorkOrderPriority, str] = {
    WorkOrderPriority.NORMAL: "Oddiy",
    WorkOrderPriority.EXPRESS: "Ekspress",
    WorkOrderPriority.EMERGENCY: "Favqulodda",
}

# Allowed transitions per Business Analysis §10.2
ALLOWED_TRANSITIONS: dict[WorkOrderStatus, frozenset[WorkOrderStatus]] = {
    WorkOrderStatus.RECEIVED: frozenset(
        {
            WorkOrderStatus.WAITING_DIAGNOSIS,
            WorkOrderStatus.DIAGNOSING,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.WAITING_DIAGNOSIS: frozenset(
        {
            WorkOrderStatus.DIAGNOSING,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.DIAGNOSING: frozenset(
        {
            WorkOrderStatus.WAITING_CUSTOMER_APPROVAL,
            WorkOrderStatus.WAITING_PARTS,
            WorkOrderStatus.REJECTED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.WAITING_CUSTOMER_APPROVAL: frozenset(
        {
            WorkOrderStatus.APPROVED,
            WorkOrderStatus.REJECTED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.APPROVED: frozenset(
        {
            WorkOrderStatus.WAITING_PARTS,
            WorkOrderStatus.REPAIRING,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.WAITING_PARTS: frozenset(
        {
            WorkOrderStatus.REPAIRING,
            WorkOrderStatus.CANCELLED,
            WorkOrderStatus.WAITING_CUSTOMER_APPROVAL,
        }
    ),
    WorkOrderStatus.REPAIRING: frozenset(
        {
            WorkOrderStatus.TESTING,
            WorkOrderStatus.WAITING_PARTS,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.TESTING: frozenset(
        {
            WorkOrderStatus.QUALITY_CHECK,
            WorkOrderStatus.REPAIRING,
        }
    ),
    WorkOrderStatus.QUALITY_CHECK: frozenset(
        {
            WorkOrderStatus.READY,
            WorkOrderStatus.REPAIRING,
        }
    ),
    WorkOrderStatus.READY: frozenset(
        {
            WorkOrderStatus.DELIVERED,
            WorkOrderStatus.REPAIRING,
        }
    ),
    WorkOrderStatus.DELIVERED: frozenset(
        {
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.WARRANTY,
        }
    ),
    WorkOrderStatus.WARRANTY: frozenset(
        {
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.REPAIRING,
        }
    ),
    WorkOrderStatus.REJECTED: frozenset(
        {
            WorkOrderStatus.DELIVERED,
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.CANCELLED: frozenset({WorkOrderStatus.ARCHIVED}),
    WorkOrderStatus.CLOSED: frozenset({WorkOrderStatus.ARCHIVED}),
    WorkOrderStatus.ARCHIVED: frozenset(),
}

NOTE_REQUIRED_STATUSES: frozenset[WorkOrderStatus] = frozenset(
    {
        WorkOrderStatus.CANCELLED,
        WorkOrderStatus.REJECTED,
    }
)


def status_label(status: str | WorkOrderStatus) -> str:
    """Return Uzbek label for a status code."""
    try:
        return STATUS_LABELS_UZ[WorkOrderStatus(status)]
    except ValueError:
        return str(status)


def priority_label(priority: str | WorkOrderPriority) -> str:
    """Return Uzbek label for a priority code."""
    try:
        return PRIORITY_LABELS_UZ[WorkOrderPriority(priority)]
    except ValueError:
        return str(priority)


def assert_transition_allowed(
    current: str | WorkOrderStatus,
    target: str | WorkOrderStatus,
    *,
    note: str | None = None,
) -> tuple[WorkOrderStatus, WorkOrderStatus]:
    """
    Validate a status transition.

    Returns the normalized (current, target) statuses.
    """
    current_status = WorkOrderStatus(current)
    target_status = WorkOrderStatus(target)
    allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if target_status not in allowed:
        raise ValidationError(
            f"Status oʻtishi taqiqlangan: {status_label(current_status)} → "
            f"{status_label(target_status)}."
        )
    if target_status in NOTE_REQUIRED_STATUSES and not (note and note.strip()):
        raise ValidationError("Bekor qilish yoki rad etish uchun izoh majburiy.")
    return current_status, target_status


def next_statuses(current: str | WorkOrderStatus) -> list[WorkOrderStatus]:
    """Return allowed next statuses for *current*."""
    current_status = WorkOrderStatus(current)
    return sorted(ALLOWED_TRANSITIONS.get(current_status, frozenset()), key=lambda s: s.value)
