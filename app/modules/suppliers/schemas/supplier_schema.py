"""Supplier and purchase order schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SupplierCreateSchema(BaseModel):
    """Create supplier payload."""

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None

    @field_validator("code", "name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Maydon boʻsh boʻlishi mumkin emas.")
        return cleaned

    @field_validator("phone", "email", "address", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class SupplierUpdateSchema(SupplierCreateSchema):
    """Update supplier payload."""

    is_active: bool = True


class PurchaseOrderLineSchema(BaseModel):
    """PO line payload."""

    inventory_item_id: int
    quantity: int = Field(ge=1)
    unit_cost: int = Field(ge=0)


class PurchaseOrderCreateSchema(BaseModel):
    """Create purchase order payload."""

    supplier_id: int
    warehouse_id: int | None = None
    lines: list[PurchaseOrderLineSchema] = Field(min_length=1)
    notes: str | None = None
    submit: bool = True

    @field_validator("notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value
