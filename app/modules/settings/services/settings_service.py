"""Settings and backup service."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from secrets import token_hex

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config.database import get_database_settings
from app.config.settings import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.phone import normalize_bot_username
from app.core.time import utc_now
from app.modules.companies.models.company import Company
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.users.models.user import Role, User
from app.modules.users.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.telegram.staff_access import is_staff_chat_allowed, normalize_staff_chat_ids


class CompanyUpdateSchema(BaseModel):
    """Update company profile."""

    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    tax_id: str | None = Field(default=None, max_length=64)
    telegram_bot_token: str | None = Field(default=None, max_length=128)
    telegram_bot_username: str | None = Field(default=None, max_length=64)
    telegram_staff_chat_ids: str | None = Field(default=None, max_length=512)
    telegram_mini_app_url: str | None = Field(default=None, max_length=512)
    cloudflare_tunnel_token: str | None = Field(default=None, max_length=1024)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Kompaniya nomi majburiy.")
        return cleaned

    @field_validator(
        "phone",
        "email",
        "address",
        "tax_id",
        "telegram_bot_token",
        "telegram_bot_username",
        "telegram_staff_chat_ids",
        "telegram_mini_app_url",
        "cloudflare_tunnel_token",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("telegram_staff_chat_ids")
    @classmethod
    def normalize_staff_ids(cls, value: str | None) -> str | None:
        return normalize_staff_chat_ids(value)

    @field_validator("telegram_mini_app_url")
    @classmethod
    def normalize_mini_app_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            return None
        lower = cleaned.lower()
        if not (lower.startswith("https://") or lower.startswith("http://127.0.0.1")):
            raise ValueError(
                "Mini App URL https:// bilan boshlanishi kerak "
                "(yoki lokal test uchun http://127.0.0.1)."
            )
        return cleaned


class SettingsService:
    """Company settings, users listing, backup and restore."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._companies = CompanyRepository(session)
        self._users = UserRepository(session)
        self._audit = AuditService(session)
        self._settings = get_settings()
        self._db_settings = get_database_settings()

    def get_company(self, company_id: int) -> Company:
        company = self._companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Kompaniya topilmadi.", entity="Company")
        return company

    def ensure_staff_pin(self, company_id: int) -> str:
        """Return existing staff PIN or create a new 6-char code."""
        company = self.get_company(company_id)
        if company.telegram_staff_pin:
            return company.telegram_staff_pin
        pin = token_hex(3).upper()  # 6 hex chars
        company.telegram_staff_pin = pin
        self._companies.save(company)
        return pin

    def regenerate_staff_pin(self, company_id: int, *, actor_id: int | None = None) -> str:
        company = self.get_company(company_id)
        pin = token_hex(3).upper()
        company.telegram_staff_pin = pin
        company.updated_by = actor_id
        self._companies.save(company)
        self._audit.record(
            "staff_pin_regenerated",
            actor_id=actor_id,
            entity_type="Company",
            entity_id=company.id,
            entity_uuid=company.uuid,
        )
        return pin

    def authenticate_staff_chat(
        self,
        company_id: int,
        *,
        chat_id: str,
    ) -> User:
        """Authenticate whitelisted staff by Telegram ID only (no PIN)."""
        company = self.get_company(company_id)
        cleaned_chat = str(chat_id or "").strip()
        if not cleaned_chat:
            raise ValidationError("Telegram ID majburiy.")
        if not is_staff_chat_allowed(company.telegram_staff_chat_ids, cleaned_chat):
            raise ValidationError(
                "Bu Telegram ID ruxsat etilmagan. Sozlamalarga qoʻshing."
            )
        user = self.resolve_staff_user(company_id, cleaned_chat)
        if user is None or not user.is_active:
            raise ValidationError("Xodim topilmadi.")
        if not user.telegram_chat_id:
            user.telegram_chat_id = cleaned_chat
            self._session.flush()
        self._audit.record(
            "staff_miniapp_login",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
            message=cleaned_chat,
        )
        return user

    def link_staff_telegram(
        self,
        company_id: int,
        *,
        username: str,
        chat_id: str,
        pin: str | None = None,
    ) -> User:
        """Bind a Telegram chat to a staff user (whitelist required; PIN ignored)."""
        _ = pin  # legacy callers may still pass pin — ignored
        company = self.get_company(company_id)
        if not is_staff_chat_allowed(company.telegram_staff_chat_ids, chat_id):
            raise ValidationError(
                "Bu Telegram ID ruxsat etilmagan. Sozlamalarga qoʻshing."
            )
        user = self._users.get_by_username(company_id, username.strip())
        if user is None or not user.is_active:
            raise ValidationError("Foydalanuvchi topilmadi.")
        previous = self._users.get_by_telegram_chat_id(company_id, chat_id)
        if previous is not None and previous.id != user.id:
            previous.telegram_chat_id = None
            self._session.flush()
        user.telegram_chat_id = str(chat_id)
        self._session.flush()
        self._audit.record(
            "staff_telegram_linked",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
            message=str(chat_id),
        )
        return user

    def resolve_staff_user(self, company_id: int, chat_id: str) -> User | None:
        """Return staff actor if chat_id is whitelisted; else None."""
        company = self.get_company(company_id)
        if not is_staff_chat_allowed(company.telegram_staff_chat_ids, chat_id):
            return None
        linked = self._users.get_by_telegram_chat_id(company_id, chat_id)
        if linked is not None:
            return linked
        return self._users.get_default_staff_actor(company_id)

    def set_mini_app_url(
        self,
        company_id: int,
        url: str | None,
        *,
        actor_id: int | None = None,
    ) -> Company:
        """Persist auto-discovered Mini App HTTPS URL."""
        company = self.get_company(company_id)
        cleaned = (url or "").strip().rstrip("/") or None
        company.telegram_mini_app_url = cleaned
        company.updated_by = actor_id
        self._companies.save(company)
        self._audit.record(
            "mini_app_url_updated",
            actor_id=actor_id,
            entity_type="Company",
            entity_id=company.id,
            entity_uuid=company.uuid,
            message=cleaned or "",
        )
        return company

    def update_company(
        self,
        company_id: int,
        payload: CompanyUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Company:
        company = self.get_company(company_id)
        company.name = payload.name
        company.phone = payload.phone
        company.email = payload.email
        company.address = payload.address
        company.tax_id = payload.tax_id
        from app.security.secrets import encrypt_secret

        company.telegram_bot_token = encrypt_secret(
            (payload.telegram_bot_token or "").strip() or None
        )
        company.telegram_bot_username = normalize_bot_username(payload.telegram_bot_username)
        company.telegram_staff_chat_ids = payload.telegram_staff_chat_ids
        # Permanent Mini App URL — boʻsh saqlash named URL ni oʻchirmasin;
        # faqat qiymat berilganda yoziladi.
        if payload.telegram_mini_app_url:
            company.telegram_mini_app_url = payload.telegram_mini_app_url
        company.cloudflare_tunnel_token = encrypt_secret(payload.cloudflare_tunnel_token)
        company.updated_by = actor_id
        self._companies.save(company)
        self._audit.record(
            "company_updated",
            actor_id=actor_id,
            entity_type="Company",
            entity_id=company.id,
            entity_uuid=company.uuid,
        )
        return company

    def list_users(self, company_id: int) -> list[User]:
        stmt = (
            select(User)
            .where(User.company_id == company_id, User.deleted_at.is_(None))
            .options(joinedload(User.role))
            .order_by(User.username)
        )
        return list(self._session.scalars(stmt).unique())

    def list_roles(self) -> list[Role]:
        from app.modules.users.models.user import Role

        stmt = (
            select(Role)
            .where(Role.deleted_at.is_(None))
            .options(joinedload(Role.permissions))
            .order_by(Role.name)
        )
        return list(self._session.scalars(stmt).unique())

    def create_user(
        self,
        company_id: int,
        *,
        username: str,
        password: str,
        full_name: str,
        role_id: int,
        actor_id: int | None = None,
    ) -> User:
        from app.modules.license.services.license_service import LicenseService
        from app.modules.users.models.user import Role
        from app.security.password import hash_password

        username = username.strip()
        full_name = full_name.strip()
        if not username or not password or not full_name:
            raise ValidationError("Foydalanuvchi, parol va ism majburiy.")
        if len(password) < 4:
            raise ValidationError("Parol kamida 4 belgidan iborat boʻlsin.")
        LicenseService(self._session).assert_can_add_user(company_id)
        if self._users.get_by_username(company_id, username) is not None:
            raise ValidationError("Bu foydalanuvchi nomi band.")
        role = self._session.scalar(
            select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
        )
        if role is None:
            raise NotFoundError("Rol topilmadi.", entity="Role")
        user = User(
            company_id=company_id,
            role_id=role.id,
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            locale="uz_UZ",
            theme="system",
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._users.add(user)
        self._audit.record(
            "user_created",
            actor_id=actor_id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
            message=username,
        )
        return user

    def set_user_active(
        self,
        user_id: int,
        *,
        is_active: bool,
        actor_id: int | None = None,
    ) -> User:
        user = self._users.get_with_role(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi.", entity="User")
        if actor_id is not None and user.id == actor_id and not is_active:
            raise ValidationError("Oʻzingizni oʻchirib boʻlmaydi.")
        user.is_active = is_active
        user.updated_by = actor_id
        self._session.flush()
        self._audit.record(
            "user_activated" if is_active else "user_deactivated",
            actor_id=actor_id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
        )
        return user

    def change_user_role(
        self,
        user_id: int,
        role_id: int,
        *,
        actor_id: int | None = None,
    ) -> User:
        from app.modules.users.models.user import Role

        user = self._users.get_with_role(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi.", entity="User")
        role = self._session.scalar(
            select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
        )
        if role is None:
            raise NotFoundError("Rol topilmadi.", entity="Role")
        user.role_id = role.id
        user.updated_by = actor_id
        self._session.flush()
        self._audit.record(
            "user_role_changed",
            actor_id=actor_id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
            message=role.code,
        )
        return user

    def create_backup(self, *, actor_id: int | None = None) -> Path:
        """Copy the SQLite database into the backups directory."""
        if self._db_settings.backend != "sqlite":
            raise ValidationError("Zaxira hozircha faqat SQLite uchun.")
        source = Path(self._db_settings.sqlite_path)
        if not source.exists():
            raise ValidationError("Maʼlumotlar bazasi fayli topilmadi.")
        backup_dir = self._settings.backups_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        target = backup_dir / f"smoxi_backup_{stamp}.db"
        shutil.copy2(source, target)
        self._audit.record(
            "backup_created",
            actor_id=actor_id,
            message=str(target.name),
        )
        return target

    def list_backups(self) -> list[Path]:
        backup_dir = self._settings.backups_dir
        if not backup_dir.exists():
            return []
        return sorted(backup_dir.glob("smoxi_backup_*.db"), reverse=True)

    def restore_backup(self, backup_path: Path, *, actor_id: int | None = None) -> Path:
        """Restore SQLite database from a backup file."""
        if self._db_settings.backend != "sqlite":
            raise ValidationError("Restore hozircha faqat SQLite uchun.")
        if not backup_path.exists():
            raise ValidationError("Zaxira fayli topilmadi.")
        target = Path(self._db_settings.sqlite_path)
        # Safety copy of current DB
        if target.exists():
            safety = target.with_suffix(
                f".pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            shutil.copy2(target, safety)
        shutil.copy2(backup_path, target)
        self._audit.record(
            "backup_restored",
            actor_id=actor_id,
            message=str(backup_path.name),
        )
        return target
