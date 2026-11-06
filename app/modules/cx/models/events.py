"""CX timeline event codes and status mapping."""

from __future__ import annotations

from app.modules.work_orders.models.status import WorkOrderStatus

# visibility
VISIBILITY_CUSTOMER = "customer"
VISIBILITY_STAFF = "staff"
VISIBILITY_INTERNAL = "internal"

# event codes (CustomerExperienceModule.md §10.2)
EVENT_DEVICE_RECEIVED = "device_received"
EVENT_TECHNICIAN_ASSIGNED = "technician_assigned"
EVENT_DIAGNOSIS_STARTED = "diagnosis_started"
EVENT_DIAGNOSIS_COMPLETED = "diagnosis_completed"
EVENT_WAITING_APPROVAL = "waiting_approval"
EVENT_CUSTOMER_APPROVED = "customer_approved"
EVENT_CUSTOMER_REJECTED = "customer_rejected"
EVENT_WAITING_PARTS = "waiting_parts"
EVENT_REPAIR_STARTED = "repair_started"
EVENT_TESTING = "testing"
EVENT_QUALITY_CONTROL = "quality_control"
EVENT_READY = "ready"
EVENT_DELIVERED = "delivered"
EVENT_WARRANTY_STARTED = "warranty_started"
EVENT_CLOSED = "closed"
EVENT_CANCELLED = "cancelled"
EVENT_NOTE_ADDED = "note_added"
EVENT_ADMIN_OVERRIDE = "admin_override"

_EVENT_LABELS_UZ: dict[str, str] = {
    EVENT_DEVICE_RECEIVED: "Qurilma qabul qilindi",
    EVENT_TECHNICIAN_ASSIGNED: "Texnik biriktirildi",
    EVENT_DIAGNOSIS_STARTED: "Diagnostika boshlandi",
    EVENT_DIAGNOSIS_COMPLETED: "Diagnostika yakunlandi",
    EVENT_WAITING_APPROVAL: "Rozilik kutilmoqda",
    EVENT_CUSTOMER_APPROVED: "Mijoz tasdiqladi",
    EVENT_CUSTOMER_REJECTED: "Mijoz rad etdi",
    EVENT_WAITING_PARTS: "Ehtiyot qism kutilmoqda",
    EVENT_REPAIR_STARTED: "Taʼmir boshlandi",
    EVENT_TESTING: "Sinov",
    EVENT_QUALITY_CONTROL: "Sifat nazorati",
    EVENT_READY: "Tayyor",
    EVENT_DELIVERED: "Topshirildi",
    EVENT_WARRANTY_STARTED: "Kafolat boshlandi",
    EVENT_CLOSED: "Yopildi",
    EVENT_CANCELLED: "Bekor qilindi",
    EVENT_NOTE_ADDED: "Izoh",
    EVENT_ADMIN_OVERRIDE: "Admin istisnosi",
}

_STATUS_TO_EVENT: dict[str, str] = {
    WorkOrderStatus.RECEIVED.value: EVENT_DEVICE_RECEIVED,
    WorkOrderStatus.WAITING_DIAGNOSIS.value: EVENT_DIAGNOSIS_STARTED,
    WorkOrderStatus.DIAGNOSING.value: EVENT_DIAGNOSIS_STARTED,
    WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value: EVENT_WAITING_APPROVAL,
    WorkOrderStatus.APPROVED.value: EVENT_CUSTOMER_APPROVED,
    WorkOrderStatus.REJECTED.value: EVENT_CUSTOMER_REJECTED,
    WorkOrderStatus.WAITING_PARTS.value: EVENT_WAITING_PARTS,
    WorkOrderStatus.REPAIRING.value: EVENT_REPAIR_STARTED,
    WorkOrderStatus.TESTING.value: EVENT_TESTING,
    WorkOrderStatus.QUALITY_CHECK.value: EVENT_QUALITY_CONTROL,
    WorkOrderStatus.READY.value: EVENT_READY,
    WorkOrderStatus.DELIVERED.value: EVENT_DELIVERED,
    WorkOrderStatus.WARRANTY.value: EVENT_WARRANTY_STARTED,
    WorkOrderStatus.CLOSED.value: EVENT_CLOSED,
    WorkOrderStatus.CANCELLED.value: EVENT_CANCELLED,
    WorkOrderStatus.ARCHIVED.value: EVENT_CLOSED,
}

# Customer-visible by default for status-driven events
_CUSTOMER_VISIBLE_EVENTS: set[str] = {
    EVENT_DEVICE_RECEIVED,
    EVENT_DIAGNOSIS_STARTED,
    EVENT_DIAGNOSIS_COMPLETED,
    EVENT_WAITING_APPROVAL,
    EVENT_CUSTOMER_APPROVED,
    EVENT_CUSTOMER_REJECTED,
    EVENT_WAITING_PARTS,
    EVENT_REPAIR_STARTED,
    EVENT_TESTING,
    EVENT_QUALITY_CONTROL,
    EVENT_READY,
    EVENT_DELIVERED,
    EVENT_WARRANTY_STARTED,
    EVENT_CLOSED,
}


def event_label(code: str) -> str:
    """Uzbek label for a timeline event code."""
    return _EVENT_LABELS_UZ.get(code, code)


def event_for_status(status: str) -> str:
    """Map work order status code to CX timeline event code."""
    return _STATUS_TO_EVENT.get(status, EVENT_NOTE_ADDED)


def default_visibility_for_event(event_code: str) -> str:
    if event_code in _CUSTOMER_VISIBLE_EVENTS:
        return VISIBILITY_CUSTOMER
    return VISIBILITY_STAFF
