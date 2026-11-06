"""Work order Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.config.constants import DEFAULT_SERVICE_PRICE
from app.modules.work_orders.models.status import WorkOrderPriority


class WorkOrderPartSchema(BaseModel):
    """Part used on a work order."""

    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(default=1, ge=1)
    cost_price: int = Field(default=0, ge=0)
    sale_price: int = Field(default=0, ge=0)
    inventory_item_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Mahsulot nomi majburiy.")
        return cleaned


class WorkOrderCreateSchema(BaseModel):
    """Payload for creating a work order from reception."""

    customer_id: int
    device_id: int | None = None
    branch_id: int | None = None
    problem_description: str = Field(min_length=3, max_length=4000)
    work_scope: str | None = None
    accessories: str | None = None
    notes: str | None = None
    priority: str = WorkOrderPriority.NORMAL.value
    estimated_cost: int | None = Field(default=DEFAULT_SERVICE_PRICE, ge=0)
    parts: list[WorkOrderPartSchema] = Field(default_factory=list)

    @field_validator("problem_description")
    @classmethod
    def strip_problem(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Nosozlik tavsifi juda qisqa.")
        return cleaned

    @field_validator("work_scope", "accessories", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return WorkOrderPriority(value).value


class WorkOrderStatusChangeSchema(BaseModel):
    """Payload for changing work order status."""

    to_status: str
    note: str | None = None
    admin_override: bool = False

    @field_validator("note", mode="before")
    @classmethod
    def empty_note_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value
