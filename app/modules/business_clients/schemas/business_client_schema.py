"""Business client schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class BusinessClientCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    credit_limit: Decimal = Field(default=Decimal("0"))
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Kompaniya nomi majburiy.")
        return cleaned

    @field_validator("tax_id", "phone", "email", "address", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class BusinessClientUpdateSchema(BusinessClientCreateSchema):
    credit_hold: bool = False
    is_active: bool = True


class ContactCreateSchema(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    email: str | None = None
    job_title: str | None = None

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Kontakt nomi majburiy.")
        return cleaned

    @field_validator("phone", "email", "job_title", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value
