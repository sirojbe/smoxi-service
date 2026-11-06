"""License activation and seat checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.time import utc_now
from app.modules.license.models.license_record import LicenseRecord
from app.modules.users.models.user import User
from app.services.audit_service import AuditService


@dataclass(frozen=True, slots=True)
class LicenseStatus:
    plan_code: str
    status: str
    seats: int
    seats_used: int
    expires_at: object | None
    license_key_masked: str
    is_valid: bool
    message: str


class LicenseService:
    """Local license validation (offline-first MVP)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    def ensure_trial(self, company_id: int, *, actor_id: int | None = None) -> LicenseRecord:
        existing = self._latest(company_id)
        if existing is not None:
            return existing
        now = utc_now()
        record = LicenseRecord(
            company_id=company_id,
            plan_code="trial",
            license_key_masked="SMOXI-TRIAL-****",
            seats=5,
            status="trial",
            activated_at=now,
            expires_at=now + timedelta(days=30),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def get_status(self, company_id: int) -> LicenseStatus:
        record = self.ensure_trial(company_id)
        used = self._count_active_users(company_id)
        now = utc_now()
        expires = record.expires_at
        if expires is not None and expires.tzinfo is None:

            expires = expires.replace(tzinfo=UTC)
        expired = expires is not None and expires < now
        status = "expired" if expired else record.status
        is_valid = not expired and status in {"trial", "active"}
        if expired:
            message = "Litsenziya muddati tugagan."
        elif used > record.seats:
            message = f"Oʻrinlar toʻldi ({used}/{record.seats})."
            is_valid = False
        else:
            message = f"{record.plan_code.upper()} · {used}/{record.seats} oʻrin"
        return LicenseStatus(
            plan_code=record.plan_code,
            status=status,
            seats=record.seats,
            seats_used=used,
            expires_at=record.expires_at,
            license_key_masked=record.license_key_masked,
            is_valid=is_valid,
            message=message,
        )

    def activate(
        self,
        company_id: int,
        license_key: str,
        *,
        actor_id: int | None = None,
    ) -> LicenseRecord:
        plan, seats, days = self._parse_key(license_key)
        now = utc_now()
        masked = self._mask(license_key)
        record = self._latest(company_id)
        if record is None:
            record = LicenseRecord(company_id=company_id, license_key_masked=masked)
            self._session.add(record)
        record.plan_code = plan
        record.license_key_masked = masked
        record.seats = seats
        record.status = "active" if plan != "trial" else "trial"
        record.activated_at = now
        record.expires_at = now + timedelta(days=days)
        record.updated_by = actor_id
        self._session.flush()
        self._audit.record(
            "license_activated",
            actor_id=actor_id,
            entity_type="License",
            entity_id=record.id,
            entity_uuid=record.uuid,
            message=f"{plan}/{seats}",
        )
        return record

    def assert_can_add_user(self, company_id: int) -> None:
        status = self.get_status(company_id)
        if not status.is_valid:
            raise ValidationError(status.message)
        if status.seats_used >= status.seats:
            raise ValidationError(
                f"Litsenziya oʻrinlari tugagan ({status.seats_used}/{status.seats})."
            )

    def _latest(self, company_id: int) -> LicenseRecord | None:
        stmt = (
            select(LicenseRecord)
            .where(
                LicenseRecord.company_id == company_id,
                LicenseRecord.deleted_at.is_(None),
            )
            .order_by(LicenseRecord.id.desc())
        )
        return self._session.scalar(stmt)

    def _count_active_users(self, company_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.company_id == company_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        return int(self._session.scalar(stmt) or 0)

    @staticmethod
    def _mask(key: str) -> str:
        cleaned = key.strip().upper()
        if len(cleaned) <= 10:
            return cleaned[:4] + "-****"
        return cleaned[:10] + "-****"

    @staticmethod
    def _parse_key(key: str) -> tuple[str, int, int]:
        cleaned = key.strip().upper().replace(" ", "")
        if not cleaned:
            raise ValidationError("Litsenziya kaliti majburiy.")
        if cleaned in {"SMOXI-TRIAL", "TRIAL"}:
            return "trial", 5, 30
        if cleaned.startswith("SMOXI-STD-") and len(cleaned) >= 14:
            return "standard", 10, 365
        if cleaned.startswith("SMOXI-ENT-") and len(cleaned) >= 14:
            return "enterprise", 50, 365
        if cleaned.startswith("SMOXI-PRO-") and len(cleaned) >= 14:
            return "professional", 25, 365
        raise ValidationError(
            "Notoʻgʻri kalit. Namuna: SMOXI-STD-XXXX yoki SMOXI-TRIAL"
        )
