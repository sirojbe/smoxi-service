"""Automation application service."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.time import utc_now
from app.modules.automation.models.rule import (
    ACTION_CALENDAR,
    ACTION_NOTIFY,
    TRIGGER_LOW_STOCK,
    TRIGGER_MANUAL,
    TRIGGER_WO_STATUS,
    AutomationRule,
    AutomationRun,
)
from app.modules.automation.repositories.rule_repository import (
    AutomationRuleRepository,
    AutomationRunRepository,
)
from app.modules.automation.schemas.rule_schema import (
    AutomationRuleCreateSchema,
    AutomationRuleUpdateSchema,
)
from app.modules.calendar.schemas.event_schema import CalendarEventCreateSchema
from app.modules.calendar.services.calendar_service import CalendarService
from app.modules.notifications.services.notification_service import NotificationService
from app.services.audit_service import AuditService


class AutomationService:
    """Manage and execute automation rules."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._rules = AutomationRuleRepository(session)
        self._runs = AutomationRunRepository(session)
        self._audit = AuditService(session)

    def list_rules(self, company_id: int) -> list[AutomationRule]:
        return self._rules.list_for_company(company_id)

    def list_runs(self, company_id: int) -> list[AutomationRun]:
        return self._runs.list_recent(company_id)

    def create_rule(
        self,
        company_id: int,
        payload: AutomationRuleCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> AutomationRule:
        row = AutomationRule(
            company_id=company_id,
            name=payload.name,
            description=payload.description,
            trigger_type=payload.trigger_type,
            trigger_value=payload.trigger_value,
            action_type=payload.action_type,
            action_payload=payload.action_payload,
            is_enabled=payload.is_enabled,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._rules.add(row)
        self._audit.record(
            "automation_rule_created",
            actor_id=actor_id,
            entity_type="AutomationRule",
            entity_id=row.id,
            entity_uuid=row.uuid,
            message=row.name,
        )
        return row

    def update_rule(
        self,
        rule_id: int,
        payload: AutomationRuleUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> AutomationRule:
        row = self._rules.require_by_id(rule_id)
        row.name = payload.name
        row.description = payload.description
        row.trigger_type = payload.trigger_type
        row.trigger_value = payload.trigger_value
        row.action_type = payload.action_type
        row.action_payload = payload.action_payload
        row.is_enabled = payload.is_enabled
        row.updated_by = actor_id
        self._rules.save(row)
        return row

    def set_enabled(
        self, rule_id: int, *, enabled: bool, actor_id: int | None = None
    ) -> AutomationRule:
        row = self._rules.require_by_id(rule_id)
        row.is_enabled = enabled
        row.updated_by = actor_id
        self._rules.save(row)
        return row

    def soft_delete(self, rule_id: int, *, actor_id: int | None = None) -> None:
        row = self._rules.require_by_id(rule_id)
        row.soft_delete(actor_id=actor_id)

    def run_rule(
        self,
        rule_id: int,
        *,
        actor_id: int | None = None,
        context: str | None = None,
    ) -> AutomationRun:
        rule = self._rules.require_by_id(rule_id)
        if not rule.is_enabled and rule.trigger_type != TRIGGER_MANUAL:
            raise ValidationError("Qoida oʻchirilgan.")
        try:
            message = self._execute(rule, context=context, actor_id=actor_id)
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            status = "failed"
        rule.last_run_at = utc_now()
        rule.run_count = int(rule.run_count or 0) + 1
        rule.updated_by = actor_id
        run = AutomationRun(
            company_id=rule.company_id,
            rule_id=rule.id,
            status=status,
            message=message,
            ran_at=utc_now(),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._runs.add(run)
        return run

    def fire_trigger(
        self,
        company_id: int,
        trigger_type: str,
        *,
        trigger_value: str | None = None,
        context: str | None = None,
        actor_id: int | None = None,
    ) -> int:
        """Execute all matching enabled rules; return count run."""
        rules = self._rules.list_by_trigger(
            company_id, trigger_type, trigger_value=trigger_value
        )
        count = 0
        for rule in rules:
            self.run_rule(rule.id, actor_id=actor_id, context=context)
            count += 1
        return count

    def seed_defaults(self, company_id: int, *, actor_id: int | None = None) -> int:
        """Create starter rules if none exist."""
        existing = self._rules.list_for_company(company_id)
        if existing:
            return 0
        defaults = [
            AutomationRuleCreateSchema(
                name="Tayyor → ichki bildirishnoma",
                description="WO ready boʻlganda xodimlarga eslatma",
                trigger_type=TRIGGER_WO_STATUS,
                trigger_value="ready",
                action_type=ACTION_NOTIFY,
                action_payload="Qurilma olib ketishga tayyor",
            ),
            AutomationRuleCreateSchema(
                name="Kam zaxira → bildirishnoma",
                trigger_type=TRIGGER_LOW_STOCK,
                action_type=ACTION_NOTIFY,
                action_payload="Ombor zaxirasini tekshiring",
            ),
            AutomationRuleCreateSchema(
                name="Qoʻlda eslatma (kalendar)",
                trigger_type=TRIGGER_MANUAL,
                action_type=ACTION_CALENDAR,
                action_payload="Avtomatik eslatma",
            ),
        ]
        for payload in defaults:
            self.create_rule(company_id, payload, actor_id=actor_id)
        return len(defaults)

    def _execute(
        self,
        rule: AutomationRule,
        *,
        context: str | None,
        actor_id: int | None,
    ) -> str:
        body = rule.action_payload or rule.name
        if context:
            body = f"{body}\n{context}"
        if rule.action_type == ACTION_NOTIFY:
            NotificationService(self._session).create(
                rule.company_id,
                title=f"Avto: {rule.name}",
                body=body[:500],
                kind="system",
                route="notifications",
                actor_id=actor_id,
            )
            return "Bildirishnoma yaratildi"
        if rule.action_type == ACTION_CALENDAR:
            start = utc_now() + timedelta(hours=1)
            CalendarService(self._session).create_event(
                rule.company_id,
                CalendarEventCreateSchema(
                    title=rule.name[:200],
                    description=body,
                    event_type="reminder",
                    starts_at=start,
                    ends_at=start + timedelta(minutes=30),
                ),
                actor_id=actor_id,
            )
            return "Kalendar eslatmasi yaratildi"
        raise ValidationError(f"Nomaʼlum amal: {rule.action_type}")
