"""Technician CX KPI aggregation (CX-H)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.technicians.models.technician import Technician
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.models.work_order import WorkOrder


@dataclass(frozen=True, slots=True)
class TechnicianKpiRow:
    technician_id: int
    full_name: str
    assigned: int
    completed: int
    ready: int
    revenue: int
    productivity_score: float


class TechnicianKpiService:
    """Compute technician performance metrics for a company."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def leaderboard(
        self,
        company_id: int,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[TechnicianKpiRow]:
        techs = list(
            self._session.scalars(
                select(Technician).where(
                    Technician.company_id == company_id,
                    Technician.deleted_at.is_(None),
                )
            )
        )
        rows: list[TechnicianKpiRow] = []
        for tech in techs:
            stmt = select(WorkOrder).where(
                WorkOrder.company_id == company_id,
                WorkOrder.technician_id == tech.id,
                WorkOrder.deleted_at.is_(None),
            )
            if date_from is not None:
                stmt = stmt.where(WorkOrder.received_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(WorkOrder.received_at <= date_to)
            orders = list(self._session.scalars(stmt))
            assigned = len(orders)
            completed = sum(
                1
                for o in orders
                if o.status
                in {
                    WorkOrderStatus.DELIVERED.value,
                    WorkOrderStatus.CLOSED.value,
                }
            )
            ready = sum(1 for o in orders if o.status == WorkOrderStatus.READY.value)
            done_statuses = {
                WorkOrderStatus.DELIVERED.value,
                WorkOrderStatus.CLOSED.value,
            }
            revenue = sum(
                int(o.final_cost or o.estimated_cost or 0)
                for o in orders
                if o.status in done_statuses
            )
            # Simple score: completed * 10 + ready * 3
            score = float(completed * 10 + ready * 3)
            rows.append(
                TechnicianKpiRow(
                    technician_id=tech.id,
                    full_name=tech.full_name,
                    assigned=assigned,
                    completed=completed,
                    ready=ready,
                    revenue=revenue,
                    productivity_score=score,
                )
            )
        rows.sort(key=lambda r: r.productivity_score, reverse=True)
        return rows
