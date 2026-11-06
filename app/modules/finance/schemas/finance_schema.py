"""Finance Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.modules.finance.models.enums import PaymentMethod


class InvoiceLineSchema(BaseModel):
    """Single invoice line."""

    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1)
    unit_price: int = Field(ge=0)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Qator tavsifi majburiy.")
        return cleaned


class InvoiceCreateSchema(BaseModel):
    """Create invoice payload."""

    customer_id: int
    work_order_id: int | None = None
    lines: list[InvoiceLineSchema] = Field(min_length=1)
    discount_amount: int = Field(default=0, ge=0)
    tax_amount: int = Field(default=0, ge=0)
    notes: str | None = None
    issue_immediately: bool = True

    @field_validator("notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class PaymentCreateSchema(BaseModel):
    """Record payment payload."""

    invoice_id: int
    amount: int = Field(ge=1)
    method: str = PaymentMethod.CASH.value
    reference: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        return PaymentMethod(value).value

    @field_validator("reference", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class CashSessionOpenSchema(BaseModel):
    """Open cash session payload."""

    opening_balance: int = Field(default=0, ge=0)
    notes: str | None = None


class CashSessionCloseSchema(BaseModel):
    """Close cash session payload."""

    closing_balance: int = Field(ge=0)
    notes: str | None = None
