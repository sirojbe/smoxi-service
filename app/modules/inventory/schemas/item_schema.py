"""Inventory Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.modules.inventory.models.enums import StockMovementType


class InventoryItemCreateSchema(BaseModel):
    """Payload for creating an inventory item."""

    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    unit: str = Field(default="dona", max_length=20)
    quantity_on_hand: int = Field(default=0, ge=0)
    min_quantity: int = Field(default=0, ge=0)
    purchase_price: int = Field(default=0, ge=0)
    sale_price: int = Field(default=0, ge=0)
    notes: str | None = None
    warehouse_id: int | None = None

    @field_validator("sku", "name", "unit")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Maydon boʻsh boʻlishi mumkin emas.")
        return cleaned

    @field_validator("category", "barcode", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class InventoryItemUpdateSchema(InventoryItemCreateSchema):
    """Payload for updating an inventory item (quantity managed via movements)."""

    is_active: bool = True


class StockAdjustSchema(BaseModel):
    """Payload for stock quantity change."""

    movement_type: str = StockMovementType.ADJUST.value
    quantity: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=64)

    @field_validator("movement_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        return StockMovementType(value).value

    @field_validator("reason", "reference", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value
