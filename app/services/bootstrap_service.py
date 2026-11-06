"""Database bootstrap for first-run installation."""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.modules.companies.models.company import Company
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.users.models.user import Permission, Role, User
from app.modules.users.repositories.user_repository import UserRepository
from app.security.password import hash_password
from app.security.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS

logger = get_logger("bootstrap")

DEFAULT_COMPANY_CODE = "smoxi"
DEFAULT_COMPANY_NAME = "SMOXI Service"
DEFAULT_ADMIN_USERNAME = "1"
DEFAULT_ADMIN_PASSWORD = "1234"


class BootstrapService:
    """Seed mandatory system data on first run."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._companies = CompanyRepository(session)

    def ensure_system_data(self) -> None:
        """Create default company, roles, permissions, and admin if missing."""
        permissions = self._ensure_permissions()
        roles = self._ensure_roles(permissions)
        if self._users.count_all() > 0:
            self._flag_weak_default_passwords()
            self._ensure_trial_licenses()
            self._ensure_default_branches()
            return

        logger.info("Birinchi ishga tushirish: tizim maʼlumotlari yaratilmoqda")
        company = self._ensure_company()
        admin_role = roles["admin"]
        self._ensure_admin_user(company.id, admin_role.id)
        self._ensure_trial_licenses()
        self._ensure_default_branches()
        self._session.flush()
        logger.info("Tizim maʼlumotlari muvaffaqiyatli yaratildi")

    def _flag_weak_default_passwords(self) -> None:
        """Force password change for accounts still using the bootstrap default."""
        from app.security.password import verify_password

        users = list(self._session.scalars(select(User).where(User.deleted_at.is_(None))))
        for user in users:
            if user.must_change_password:
                continue
            try:
                if verify_password(DEFAULT_ADMIN_PASSWORD, user.password_hash):
                    user.must_change_password = True
                    logger.warning(
                        "Zaif default parol aniqlandi (user={}): almashtirish majburiy",
                        user.username,
                    )
            except Exception:  # noqa: BLE001
                continue

    def _ensure_trial_licenses(self) -> None:
        from app.modules.license.services.license_service import LicenseService

        companies = list(self._session.scalars(select(Company)))
        license_svc = LicenseService(self._session)
        for company in companies:
            license_svc.ensure_trial(company.id)

    def _ensure_default_branches(self) -> None:
        from app.modules.branches.services.branch_service import BranchService

        companies = list(self._session.scalars(select(Company)))
        branch_svc = BranchService(self._session)
        for company in companies:
            branch_svc.ensure_default(company.id)
    def _ensure_company(self) -> Company:
        existing = self._companies.get_by_code(DEFAULT_COMPANY_CODE)
        if existing:
            return existing
        company = Company(
            name=DEFAULT_COMPANY_NAME,
            code=DEFAULT_COMPANY_CODE,
            is_active=True,
        )
        return self._companies.add(company)

    def _ensure_permissions(self) -> dict[str, Permission]:
        result: dict[str, Permission] = {}
        for code in ALL_PERMISSIONS:
            permission = self._session.scalar(
                select(Permission).where(Permission.code == code)
            )
            if permission is None:
                permission = Permission(code=code, description=code)
                self._session.add(permission)
                self._session.flush()
            result[code] = permission
        return result

    def _ensure_roles(self, permissions: dict[str, Permission]) -> dict[str, Role]:
        result: dict[str, Role] = {}
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = self._session.scalar(select(Role).where(Role.code == role_code))
            if role is None:
                role = Role(
                    code=role_code,
                    name=self._role_display_name(role_code),
                    is_system=True,
                )
                self._session.add(role)
                self._session.flush()
            role.permissions = [permissions[code] for code in perm_codes if code in permissions]
            result[role_code] = role
        return result

    def _ensure_admin_user(self, company_id: int, role_id: int) -> User:
        password = os.environ.get("SMOXI_ADMIN_INITIAL_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        force_change = password == DEFAULT_ADMIN_PASSWORD
        if force_change:
            logger.warning(
                "Admin default parol bilan yaratildi — birinchi kirishda almashtirish majburiy"
            )
        user = User(
            company_id=company_id,
            role_id=role_id,
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(password),
            full_name="Tizim administratori",
            locale="uz_UZ",
            theme="system",
            is_active=True,
            must_change_password=force_change,
        )
        return self._users.add(user)

    @staticmethod
    def _role_display_name(code: str) -> str:
        names = {
            "owner": "Egasi",
            "admin": "Administrator",
            "manager": "Menejer",
            "reception": "Qabulxona",
            "technician": "Texnik",
            "warehouse": "Ombor",
            "accountant": "Hisobchi",
        }
        return names.get(code, code)
