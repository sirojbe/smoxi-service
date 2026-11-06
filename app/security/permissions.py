"""System permission keys."""

from __future__ import annotations

from typing import Final

# Auth & users
AUTH_LOGIN: Final[str] = "auth.login"
USERS_VIEW: Final[str] = "users.view"
USERS_MANAGE: Final[str] = "users.manage"

# Dashboard
DASHBOARD_VIEW: Final[str] = "dashboard.view"

# Settings & admin
SETTINGS_VIEW: Final[str] = "settings.view"
SETTINGS_MANAGE: Final[str] = "settings.manage"
ADMIN_VIEW: Final[str] = "admin.view"

# Operational modules (expanded as modules ship)
CUSTOMERS_VIEW: Final[str] = "customers.view"
CUSTOMERS_MANAGE: Final[str] = "customers.manage"
COMPANIES_VIEW: Final[str] = "companies.view"
COMPANIES_MANAGE: Final[str] = "companies.manage"
WORK_ORDERS_VIEW: Final[str] = "work_orders.view"
WORK_ORDERS_MANAGE: Final[str] = "work_orders.manage"
INVENTORY_VIEW: Final[str] = "inventory.view"
INVENTORY_MANAGE: Final[str] = "inventory.manage"
FINANCE_VIEW: Final[str] = "finance.view"
FINANCE_MANAGE: Final[str] = "finance.manage"
REPORTS_VIEW: Final[str] = "reports.view"
LICENSE_VIEW: Final[str] = "license.view"
LICENSE_MANAGE: Final[str] = "license.manage"

ALL_PERMISSIONS: Final[tuple[str, ...]] = (
    AUTH_LOGIN,
    USERS_VIEW,
    USERS_MANAGE,
    DASHBOARD_VIEW,
    SETTINGS_VIEW,
    SETTINGS_MANAGE,
    ADMIN_VIEW,
    CUSTOMERS_VIEW,
    CUSTOMERS_MANAGE,
    COMPANIES_VIEW,
    COMPANIES_MANAGE,
    WORK_ORDERS_VIEW,
    WORK_ORDERS_MANAGE,
    INVENTORY_VIEW,
    INVENTORY_MANAGE,
    FINANCE_VIEW,
    FINANCE_MANAGE,
    REPORTS_VIEW,
    LICENSE_VIEW,
    LICENSE_MANAGE,
)

ROLE_PERMISSIONS: Final[dict[str, tuple[str, ...]]] = {
    "owner": ALL_PERMISSIONS,
    "admin": ALL_PERMISSIONS,
    "manager": (
        DASHBOARD_VIEW,
        CUSTOMERS_VIEW,
        CUSTOMERS_MANAGE,
        COMPANIES_VIEW,
        COMPANIES_MANAGE,
        WORK_ORDERS_VIEW,
        WORK_ORDERS_MANAGE,
        INVENTORY_VIEW,
        FINANCE_VIEW,
        REPORTS_VIEW,
        SETTINGS_VIEW,
        LICENSE_VIEW,
        USERS_VIEW,
    ),
    "reception": (
        DASHBOARD_VIEW,
        CUSTOMERS_VIEW,
        CUSTOMERS_MANAGE,
        COMPANIES_VIEW,
        WORK_ORDERS_VIEW,
        WORK_ORDERS_MANAGE,
    ),
    "technician": (
        DASHBOARD_VIEW,
        WORK_ORDERS_VIEW,
        WORK_ORDERS_MANAGE,
        INVENTORY_VIEW,
    ),
    "warehouse": (
        DASHBOARD_VIEW,
        INVENTORY_VIEW,
        INVENTORY_MANAGE,
    ),
    "accountant": (
        DASHBOARD_VIEW,
        FINANCE_VIEW,
        FINANCE_MANAGE,
        REPORTS_VIEW,
        COMPANIES_VIEW,
    ),
}
