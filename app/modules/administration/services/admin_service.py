"""Administration — audit log viewer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AdministrationService:
    """Read-only administration queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_audit(
        self,
        *,
        query: str | None = None,
        limit: int = 200,
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        rows = list(self._session.scalars(stmt))
        if not query:
            return rows
        q = query.strip().lower()
        return [
            r
            for r in rows
            if q in (r.action or "").lower()
            or q in (r.entity_type or "").lower()
            or q in (r.message or "").lower()
            or q in str(r.actor_id or "")
        ]
