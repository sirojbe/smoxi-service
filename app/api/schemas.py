"""API Pydantic schemas (v1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    company_code: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    company_id: int
    full_name: str


class MeResponse(BaseModel):
    id: int
    username: str
    full_name: str
    company_id: int


class WorkOrderOut(BaseModel):
    id: int
    uuid: str
    number: str
    status: str
    customer_id: int
    problem_description: str | None
    estimated_cost: int | None
    sync_status: str
    version: int
    updated_at: datetime | None


class CustomerOut(BaseModel):
    id: int
    uuid: str
    display_name: str
    phone: str
    email: str | None
    sync_status: str
    version: int
    updated_at: datetime | None


class SyncEntity(BaseModel):
    entity_type: str
    id: int
    uuid: str
    version: int
    sync_status: str
    updated_at: datetime | None
    payload: dict


class SyncPullResponse(BaseModel):
    server_time: datetime
    entities: list[SyncEntity]


class SyncAckItem(BaseModel):
    entity_type: str
    uuid: str
    version: int
    status: str = "synced"  # synced | conflict | failed


class SyncPushRequest(BaseModel):
    acks: list[SyncAckItem] = Field(default_factory=list)


class SyncPushResponse(BaseModel):
    accepted: int
    conflicts: int
