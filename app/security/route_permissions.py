"""Sidebar route → permission mapping."""

from __future__ import annotations

from typing import Final

from app.security.permissions import (
    ADMIN_VIEW,
    COMPANIES_VIEW,
    CUSTOMERS_VIEW,
    DASHBOARD_VIEW,
    FINANCE_VIEW,
    INVENTORY_MANAGE,
    INVENTORY_VIEW,
    REPORTS_VIEW,
    SETTINGS_MANAGE,
    SETTINGS_VIEW,
    WORK_ORDERS_MANAGE,
    WORK_ORDERS_VIEW,
)

# None = any authenticated user
ROUTE_PERMISSIONS: Final[dict[str, str | None]] = {
    "dashboard": DASHBOARD_VIEW,
    "customers": CUSTOMERS_VIEW,
    "companies": COMPANIES_VIEW,
    "reception": WORK_ORDERS_MANAGE,
    "work_orders": WORK_ORDERS_VIEW,
    "technicians": WORK_ORDERS_VIEW,
    "inventory": INVENTORY_VIEW,
    "warehouse": INVENTORY_VIEW,
    "suppliers": INVENTORY_MANAGE,
    "finance": FINANCE_VIEW,
    "payments": FINANCE_VIEW,
    "reports": REPORTS_VIEW,
    "calendar": None,
    "notifications": None,
    "telegram": SETTINGS_VIEW,
    "automation": SETTINGS_MANAGE,
    "ai_assistant": None,
    "settings": SETTINGS_VIEW,
    "administration": ADMIN_VIEW,
    "sync": SETTINGS_VIEW,
    "help": None,
    "about": None,
    "logout": None,
}


def allowed_routes(permission_codes: set[str]) -> set[str]:
    """Return route ids visible for the given permission set."""
    allowed: set[str] = set()
    for route, required in ROUTE_PERMISSIONS.items():
        if required is None or required in permission_codes:
            allowed.add(route)
    return allowed
