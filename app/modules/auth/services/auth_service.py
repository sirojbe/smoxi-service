"""Authentication service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.security import get_security_settings
from app.core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from app.core.time import utc_now
from app.modules.auth.models.session import UserSession
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.users.models.user import User
from app.modules.users.repositories.user_repository import UserRepository
from app.security.password import generate_session_token, hash_password, verify_password
from app.services.audit_service import AuditService

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_HOURS = 8
WEAK_DEFAULT_PASSWORD = "1234"


@dataclass(frozen=True)
class AuthResult:
    """Successful authentication payload."""

    user: User
    session_token: str


class AuthService:
    """Handle login, logout, and session validation."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._companies = CompanyRepository(session)
        self._audit = AuditService(session)
        self._security = get_security_settings()

    def login(
        self,
        *,
        company_code: str,
        username: str,
        password: str,
        remember_me: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthResult:
        """Authenticate credentials and create a session."""
        company = self._companies.get_by_code(company_code.strip().lower())
        if company is None or not company.is_active:
            raise AuthenticationError("Kompaniya topilmadi yoki faol emas.")

        user = self._users.get_by_username(company.id, username.strip())
        if user is None:
            self._audit.record("login_failed", message=f"username={username}")
            raise AuthenticationError("Login yoki parol notoʻgʻri.")

        self._ensure_not_locked(user)

        if not verify_password(password, user.password_hash):
            self._register_failed_attempt(user)
            raise AuthenticationError("Login yoki parol notoʻgʻri.")

        if not user.is_active:
            raise AuthenticationError("Foydalanuvchi hisobi faol emas.")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = utc_now()
        self._users.save(user)

        token = generate_session_token()
        expires_hours = SESSION_HOURS * (7 if remember_me else 1)
        user_session = UserSession(
            user_id=user.id,
            token_hash=self._hash_token(token),
            expires_at=utc_now() + timedelta(hours=expires_hours),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(user_session)
        self._session.flush()

        self._audit.record(
            "login",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
            ip_address=ip_address,
        )
        return AuthResult(user=user, session_token=token)

    def verify_user_password(self, user_id: int, password: str) -> User:
        """Verify password for an already authenticated user (lock screen)."""
        user = self._users.get_with_role(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas.")
        if not verify_password(password, user.password_hash):
            self._audit.record(
                "unlock_failed",
                actor_id=user.id,
                entity_type="User",
                entity_id=user.id,
            )
            raise AuthenticationError("Parol notoʻgʻri.")
        self._audit.record(
            "unlock",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
        )
        return user

    def logout(self, session_token: str, *, actor_id: int | None = None) -> None:
        """Revoke an active session."""
        user_session = self._get_active_session(session_token)
        if user_session is not None:
            user_session.revoked_at = utc_now()
            self._audit.record(
                "logout",
                actor_id=actor_id or user_session.user_id,
                entity_type="User",
                entity_id=user_session.user_id,
            )

    def validate_session(self, session_token: str) -> User:
        """Return the user for a valid session token."""
        user_session = self._get_active_session(session_token)
        if user_session is None:
            raise AuthenticationError("Sessiya muddati tugagan yoki yaroqsiz.")
        user = self._users.get_with_role(user_session.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas.")
        return user

    def change_password(
        self,
        user_id: int,
        *,
        current_password: str,
        new_password: str,
    ) -> User:
        """Update password and clear the must-change flag."""
        user = self._users.get_with_role(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas.")
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Joriy parol notoʻgʻri.")
        self._validate_new_password(new_password, current_password)
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        self._users.save(user)
        self._audit.record(
            "password_changed",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
            entity_uuid=user.uuid,
        )
        return user

    def user_has_permission(self, user: User, permission_code: str) -> bool:
        """Return True if *user* has *permission_code*."""
        return any(perm.code == permission_code for perm in (user.role.permissions if user.role else []))

    def require_permission(self, user: User, permission_code: str) -> None:
        """Raise AuthorizationError when permission is missing."""
        if not self.user_has_permission(user, permission_code):
            raise AuthorizationError(
                "Bu amalni bajarish uchun ruxsatingiz yoʻq.",
                permission=permission_code,
            )

    def _get_active_session(self, session_token: str) -> UserSession | None:
        token_hash = self._hash_token(session_token)
        user_session = self._session.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > utc_now(),
            )
        )
        return user_session

    def _ensure_not_locked(self, user: User) -> None:
        if user.locked_until and user.locked_until > utc_now():
            raise AuthenticationError("Hisob vaqtincha bloklangan. Keyinroq urinib koʻring.")

    def _register_failed_attempt(self, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = utc_now() + timedelta(minutes=LOCKOUT_MINUTES)
        self._users.save(user)
        self._audit.record(
            "login_failed",
            actor_id=user.id,
            entity_type="User",
            entity_id=user.id,
            message=f"attempts={user.failed_login_attempts}",
        )

    def _validate_new_password(self, new_password: str, current_password: str) -> None:
        min_len = max(4, int(self._security.password_min_length))
        cleaned = (new_password or "").strip()
        if len(cleaned) < min_len:
            raise ValidationError(
                f"Yangi parol kamida {min_len} belgidan iborat boʻlishi kerak."
            )
        if cleaned == current_password:
            raise ValidationError("Yangi parol joriy paroldan farq qilishi kerak.")
        if cleaned == WEAK_DEFAULT_PASSWORD:
            raise ValidationError("Zaif default parolni (1234) ishlatish mumkin emas.")
        if self._security.password_require_special and cleaned.isalnum():
            raise ValidationError(
                "Yangi parolda kamida bitta maxsus belgi boʻlishi kerak."
            )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
