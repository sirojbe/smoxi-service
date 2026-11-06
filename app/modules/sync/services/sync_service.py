"""Cloud sync application service."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import SyncAckItem, SyncEntity, SyncPullResponse, SyncPushResponse
from app.core.enums import SyncStatus
from app.core.time import utc_now
from app.modules.customers.models.customer import Customer
from app.modules.work_orders.models.work_order import WorkOrder


class SyncService:
    """
    Offline-first sync foundation.

    Pull returns pending/failed/conflict rows for a company.
    Push accepts client acks and marks entities synced (or conflict).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def pull(
        self,
        company_id: int,
        *,
        since: datetime | None = None,
        limit: int = 200,
    ) -> SyncPullResponse:
        entities: list[SyncEntity] = []
        entities.extend(self._pull_work_orders(company_id, since=since, limit=limit))
        remaining = max(0, limit - len(entities))
        if remaining:
            entities.extend(
                self._pull_customers(company_id, since=since, limit=remaining)
            )
        return SyncPullResponse(server_time=utc_now(), entities=entities)

    def push_acks(
        self, company_id: int, acks: list[SyncAckItem]
    ) -> SyncPushResponse:
        accepted = 0
        conflicts = 0
        for ack in acks:
            row = self._resolve(company_id, ack.entity_type, ack.uuid)
            if row is None:
                conflicts += 1
                continue
            if int(getattr(row, "version", 0) or 0) != ack.version:
                row.sync_status = SyncStatus.CONFLICT.value
                conflicts += 1
                continue
            if ack.status == SyncStatus.SYNCED.value:
                row.sync_status = SyncStatus.SYNCED.value
                accepted += 1
            elif ack.status == SyncStatus.CONFLICT.value:
                row.sync_status = SyncStatus.CONFLICT.value
                conflicts += 1
            else:
                row.sync_status = SyncStatus.FAILED.value
                conflicts += 1
        self._session.flush()
        return SyncPushResponse(accepted=accepted, conflicts=conflicts)

    def count_pending(self, company_id: int) -> int:
        wo = self._session.scalar(
            select(WorkOrder.id)
            .where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.sync_status != SyncStatus.SYNCED.value,
            )
            .limit(500)
        )
        # cheap counts
        from sqlalchemy import func

        wo_count = int(
            self._session.scalar(
                select(func.count())
                .select_from(WorkOrder)
                .where(
                    WorkOrder.company_id == company_id,
                    WorkOrder.deleted_at.is_(None),
                    WorkOrder.sync_status != SyncStatus.SYNCED.value,
                )
            )
            or 0
        )
        cu_count = int(
            self._session.scalar(
                select(func.count())
                .select_from(Customer)
                .where(
                    Customer.company_id == company_id,
                    Customer.deleted_at.is_(None),
                    Customer.sync_status != SyncStatus.SYNCED.value,
                )
            )
            or 0
        )
        _ = wo
        return wo_count + cu_count

    def _pull_work_orders(
        self,
        company_id: int,
        *,
        since: datetime | None,
        limit: int,
    ) -> list[SyncEntity]:
        stmt = (
            select(WorkOrder)
            .where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.sync_status != SyncStatus.SYNCED.value,
            )
            .order_by(WorkOrder.updated_at.asc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(WorkOrder.updated_at >= since)
        rows = list(self._session.scalars(stmt))
        return [
            SyncEntity(
                entity_type="work_order",
                id=r.id,
                uuid=r.uuid,
                version=r.version,
                sync_status=r.sync_status,
                updated_at=r.updated_at,
                payload={
                    "number": r.number,
                    "status": r.status,
                    "customer_id": r.customer_id,
                    "estimated_cost": r.estimated_cost,
                    "problem_description": r.problem_description,
                },
            )
            for r in rows
        ]

    def _pull_customers(
        self,
        company_id: int,
        *,
        since: datetime | None,
        limit: int,
    ) -> list[SyncEntity]:
        stmt = (
            select(Customer)
            .where(
                Customer.company_id == company_id,
                Customer.deleted_at.is_(None),
                Customer.sync_status != SyncStatus.SYNCED.value,
            )
            .order_by(Customer.updated_at.asc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(Customer.updated_at >= since)
        rows = list(self._session.scalars(stmt))
        return [
            SyncEntity(
                entity_type="customer",
                id=r.id,
                uuid=r.uuid,
                version=r.version,
                sync_status=r.sync_status,
                updated_at=r.updated_at,
                payload={
                    "display_name": r.display_name,
                    "phone": r.phone,
                    "email": r.email,
                },
            )
            for r in rows
        ]

    def _resolve(self, company_id: int, entity_type: str, uuid: str) -> object | None:
        if entity_type == "work_order":
            return self._session.scalar(
                select(WorkOrder).where(
                    WorkOrder.company_id == company_id,
                    WorkOrder.uuid == uuid,
                    WorkOrder.deleted_at.is_(None),
                )
            )
        if entity_type == "customer":
            return self._session.scalar(
                select(Customer).where(
                    Customer.company_id == company_id,
                    Customer.uuid == uuid,
                    Customer.deleted_at.is_(None),
                )
            )
        return None
