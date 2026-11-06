"""Automation repositories."""

from __future__ import annotations

from app.modules.automation.models.rule import AutomationRule, AutomationRun
from app.repositories.base import BaseRepository


class AutomationRuleRepository(BaseRepository[AutomationRule]):
    model = AutomationRule

    def list_for_company(
        self, company_id: int, *, enabled_only: bool = False
    ) -> list[AutomationRule]:
        stmt = (
            self._base_query()
            .where(AutomationRule.company_id == company_id)
            .order_by(AutomationRule.name.asc())
        )
        if enabled_only:
            stmt = stmt.where(AutomationRule.is_enabled.is_(True))
        return list(self._session.scalars(stmt))

    def list_by_trigger(
        self, company_id: int, trigger_type: str, *, trigger_value: str | None = None
    ) -> list[AutomationRule]:
        stmt = (
            self._base_query()
            .where(
                AutomationRule.company_id == company_id,
                AutomationRule.is_enabled.is_(True),
                AutomationRule.trigger_type == trigger_type,
            )
            .order_by(AutomationRule.id.asc())
        )
        rows = list(self._session.scalars(stmt))
        if trigger_value is None:
            return rows
        return [
            r
            for r in rows
            if r.trigger_value is None or r.trigger_value == trigger_value
        ]


class AutomationRunRepository(BaseRepository[AutomationRun]):
    model = AutomationRun

    def list_recent(self, company_id: int, *, limit: int = 50) -> list[AutomationRun]:
        stmt = (
            self._base_query()
            .where(AutomationRun.company_id == company_id)
            .order_by(AutomationRun.ran_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
