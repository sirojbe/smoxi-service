"""Structured audit logging service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.models.audit_log import AuditLog

logger = get_logger("audit")


class AuditService:
    """Persist and emit audit events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        action: str,
        *,
        actor_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        entity_uuid: str | None = None,
        message: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry and write a structured log line."""
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_uuid=entity_uuid,
            message=message,
            ip_address=ip_address,
        )
        self._session.add(entry)
        self._session.flush()
        logger.info(
            "audit action={action} actor_id={actor_id} entity={entity_type}:{entity_id}",
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return entry
