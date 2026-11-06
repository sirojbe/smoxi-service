"""Work order public QR token helpers (CX-A / Feature 12 foundation)."""

from __future__ import annotations

import secrets

from sqlalchemy.orm import Session

from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.work_orders.models.work_order import WorkOrder
from app.services.audit_service import AuditService


def generate_public_token() -> str:
    """Opaque URL-safe token for WO QR / future public portal."""
    return secrets.token_urlsafe(16)


def build_qr_payload(work_order: WorkOrder, *, company_code: str) -> str:
    """
    Encode scan payload for CX QR.

    Format: SMOXI|company_code|WO-number|public_token
    Public portal (CX-I) will resolve by token; desktop can match number+token.
    """
    token = (work_order.public_token or "").strip()
    return f"SMOXI|{company_code}|{work_order.number}|{token}"


class WorkOrderQrService:
    """Ensure WO has public_token and build QR payload text."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._companies = CompanyRepository(session)
        self._audit = AuditService(session)

    def ensure_public_token(
        self,
        work_order: WorkOrder,
        *,
        actor_id: int | None = None,
    ) -> str:
        if (work_order.public_token or "").strip():
            return work_order.public_token  # type: ignore[return-value]
        token = generate_public_token()
        work_order.public_token = token
        work_order.updated_by = actor_id
        self._session.flush()
        self._audit.record(
            "work_order_qr_token_created",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=work_order.number,
        )
        return token

    def qr_payload_for(self, work_order: WorkOrder) -> str:
        company = self._companies.get_by_id(work_order.company_id)
        code = company.code if company else "SMOXI"
        self.ensure_public_token(work_order)
        return build_qr_payload(work_order, company_code=code)
