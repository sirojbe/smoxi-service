"""ORM model package — import all models for metadata registration."""

from app.models.audit_log import AuditLog
from app.models.base import AuditMixin, Base
from app.modules.auth.models.session import UserSession
from app.modules.automation.models.rule import AutomationRule, AutomationRun
from app.modules.branches.models.branch import Branch
from app.modules.business_clients.models.business_client import (
    BusinessClient,
    BusinessClientContact,
)
from app.modules.calendar.models.event import CalendarEvent
from app.modules.companies.models.company import Company
from app.modules.customers.models.customer import Customer
from app.modules.customers.models.device import Device
from app.modules.cx.models import WorkOrderTimelineEvent
from app.modules.cx.models.cx_entities import (
    CustomerSignature,
    IntakeSnapshot,
    MediaAsset,
    NotificationDelivery,
    PartReservation,
    ReceiptDocument,
    WarrantyCard,
)
from app.modules.finance.models.invoice import CashSession, Invoice, InvoiceLine, Payment
from app.modules.inventory.models.item import InventoryItem, StockMovement
from app.modules.inventory.models.warehouse import Warehouse
from app.modules.license.models.license_record import LicenseRecord
from app.modules.notifications.models.notification import InAppNotification
from app.modules.suppliers.models.supplier import PurchaseOrder, PurchaseOrderLine, Supplier
from app.modules.technicians.models.technician import Technician
from app.modules.telegram.models.message import TelegramMessage
from app.modules.users.models.user import Permission, Role, User
from app.modules.work_orders.models.work_order import (
    WorkOrder,
    WorkOrderPart,
    WorkOrderStatusHistory,
)

__all__ = [
    "AuditLog",
    "AuditMixin",
    "AutomationRule",
    "AutomationRun",
    "Base",
    "Branch",
    "BusinessClient",
    "BusinessClientContact",
    "CalendarEvent",
    "CashSession",
    "Company",
    "Customer",
    "CustomerSignature",
    "Device",
    "InAppNotification",
    "IntakeSnapshot",
    "InventoryItem",
    "Invoice",
    "InvoiceLine",
    "LicenseRecord",
    "MediaAsset",
    "NotificationDelivery",
    "PartReservation",
    "Payment",
    "Permission",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "ReceiptDocument",
    "Role",
    "StockMovement",
    "Supplier",
    "Technician",
    "TelegramMessage",
    "User",
    "UserSession",
    "Warehouse",
    "WarrantyCard",
    "WorkOrder",
    "WorkOrderPart",
    "WorkOrderStatusHistory",
    "WorkOrderTimelineEvent",
]
