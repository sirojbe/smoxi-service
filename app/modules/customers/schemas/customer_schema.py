"""Customer and device Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CustomerCreateSchema(BaseModel):
    """Payload for creating a customer."""

    display_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    customer_type: str = Field(default="individual", max_length=20)
    tax_id: str | None = Field(default=None, max_length=64)

    @field_validator("display_name", "phone")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Maydon boʻsh boʻlishi mumkin emas.")
        return cleaned

    @field_validator("email", "address", "tax_id", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class CustomerUpdateSchema(CustomerCreateSchema):
    """Payload for updating a customer."""

    is_active: bool = True
    is_blacklisted: bool = False


class DeviceCreateSchema(BaseModel):
    """Payload for creating a device."""

    device_type: str = Field(default="phone", max_length=64)
    brand: str | None = Field(default=None, max_length=100)
    model: str = Field(min_length=1, max_length=150)
    serial_number: str | None = Field(default=None, max_length=100)
    imei: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    access_code: str | None = Field(default=None, max_length=100)

    @field_validator("model")
    @classmethod
    def strip_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Model majburiy.")
        return cleaned

    @field_validator(
        "brand",
        "serial_number",
        "imei",
        "color",
        "notes",
        "access_code",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class DeviceUpdateSchema(DeviceCreateSchema):
    """Payload for updating a device."""
