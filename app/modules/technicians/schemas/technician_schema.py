"""Technician schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TechnicianCreateSchema(BaseModel):
    """Create technician payload."""

    code: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    skills: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_available: bool = True

    @field_validator("code", "full_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Maydon boʻsh boʻlishi mumkin emas.")
        return cleaned

    @field_validator("phone", "skills", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class TechnicianUpdateSchema(TechnicianCreateSchema):
    """Update technician payload."""

    is_active: bool = True
