"""Automation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.modules.automation.models.rule import (
    ACTION_CALENDAR,
    ACTION_NOTIFY,
    TRIGGER_LOW_STOCK,
    TRIGGER_MANUAL,
    TRIGGER_WO_STATUS,
)

_TRIGGERS = {TRIGGER_WO_STATUS, TRIGGER_LOW_STOCK, TRIGGER_MANUAL}
_ACTIONS = {ACTION_NOTIFY, ACTION_CALENDAR}


class AutomationRuleCreateSchema(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    trigger_type: str = TRIGGER_MANUAL
    trigger_value: str | None = None
    action_type: str = ACTION_NOTIFY
    action_payload: str | None = None
    is_enabled: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Nom juda qisqa.")
        return cleaned

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger(cls, value: str) -> str:
        if value not in _TRIGGERS:
            raise ValueError("Notoʻgʻri trigger.")
        return value

    @field_validator("action_type")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in _ACTIONS:
            raise ValueError("Notoʻgʻri amal.")
        return value

    @field_validator("description", "trigger_value", "action_payload", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class AutomationRuleUpdateSchema(AutomationRuleCreateSchema):
    pass
