"""API v1 routers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.errors import http_error
from app.api.schemas import (
    CustomerOut,
    LoginRequest,
    LoginResponse,
    MeResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    WorkOrderOut,
)
from app.core.exceptions import AuthenticationError
from app.modules.auth.services.auth_service import AuthService
from app.modules.customers.services.customer_service import CustomerService
from app.modules.sync.services.sync_service import SyncService
from app.modules.users.models.user import User
from app.modules.work_orders.services.work_order_service import WorkOrderService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "api": "v1"}


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    try:
        result = AuthService(db).login(
            company_code=body.company_code,
            username=body.username,
            password=body.password,
        )
    except AuthenticationError as exc:
        raise http_error(401, "login_failed", exc.message) from exc
    return LoginResponse(
        access_token=result.session_token,
        user_id=result.user.id,
        company_id=result.user.company_id,
        full_name=result.user.full_name,
    )


@router.get("/auth/me", response_model=MeResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        company_id=user.company_id,
    )


@router.get("/work-orders", response_model=list[WorkOrderOut])
def list_work_orders(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WorkOrderOut]:
    rows = WorkOrderService(db).list_work_orders(
        user.company_id, query=q, status=status
    )[:limit]
    return [
        WorkOrderOut(
            id=r.id,
            uuid=r.uuid,
            number=r.number,
            status=r.status,
            customer_id=r.customer_id,
            problem_description=r.problem_description,
            estimated_cost=r.estimated_cost,
            sync_status=r.sync_status,
            version=r.version,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
) -> list[CustomerOut]:
    rows = CustomerService(db).list_customers(user.company_id, query=q)
    return [
        CustomerOut(
            id=r.id,
            uuid=r.uuid,
            display_name=r.display_name,
            phone=r.phone,
            email=r.email,
            sync_status=r.sync_status,
            version=r.version,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/sync/pull", response_model=SyncPullResponse)
def sync_pull(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    since: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> SyncPullResponse:
    return SyncService(db).pull(user.company_id, since=since, limit=limit)


@router.post("/sync/push", response_model=SyncPushResponse)
def sync_push(
    body: SyncPushRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SyncPushResponse:
    return SyncService(db).push_acks(user.company_id, body.acks)


@router.get("/sync/pending-count")
def sync_pending_count(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    return {"pending": SyncService(db).count_pending(user.company_id)}
