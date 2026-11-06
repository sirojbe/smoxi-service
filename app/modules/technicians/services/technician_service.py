"""Technician application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.cx.models.events import (
    EVENT_TECHNICIAN_ASSIGNED,
    VISIBILITY_STAFF,
    event_label,
)
from app.modules.cx.models.timeline_event import WorkOrderTimelineEvent
from app.modules.technicians.models.technician import Technician
from app.modules.technicians.repositories.technician_repository import TechnicianRepository
from app.modules.technicians.schemas.technician_schema import (
    TechnicianCreateSchema,
    TechnicianUpdateSchema,
)
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService


class TechnicianService:
    """Technician CRUD and work-order assignment."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._technicians = TechnicianRepository(session)
        self._work_orders = WorkOrderRepository(session)
        self._audit = AuditService(session)

    def list_technicians(self, company_id: int, *, query: str | None = None) -> list[Technician]:
        return self._technicians.search(company_id, query=query)

    def list_available(self, company_id: int) -> list[Technician]:
        return self._technicians.list_available(company_id)

    def get_technician(self, technician_id: int) -> Technician:
        tech = self._technicians.get_by_id(technician_id)
        if tech is None:
            raise NotFoundError("Texnik topilmadi.", entity="Technician")
        return tech

    def create_technician(
        self,
        company_id: int,
        payload: TechnicianCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Technician:
        if self._technicians.get_by_code(company_id, payload.code) is not None:
            raise ConflictError(f"Kod allaqachon mavjud: {payload.code}")
        tech = Technician(
            company_id=company_id,
            code=payload.code,
            full_name=payload.full_name,
            phone=payload.phone,
            skills=payload.skills,
            notes=payload.notes,
            is_available=payload.is_available,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._technicians.add(tech)
        self._audit.record(
            "technician_created",
            actor_id=actor_id,
            entity_type="Technician",
            entity_id=tech.id,
            entity_uuid=tech.uuid,
            message=tech.full_name,
        )
        return tech

    def update_technician(
        self,
        technician_id: int,
        payload: TechnicianUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Technician:
        tech = self.get_technician(technician_id)
        duplicate = self._technicians.get_by_code(tech.company_id, payload.code)
        if duplicate is not None and duplicate.id != tech.id:
            raise ConflictError(f"Kod allaqachon mavjud: {payload.code}")
        tech.code = payload.code
        tech.full_name = payload.full_name
        tech.phone = payload.phone
        tech.skills = payload.skills
        tech.notes = payload.notes
        tech.is_available = payload.is_available
        tech.is_active = payload.is_active
        tech.updated_by = actor_id
        self._technicians.save(tech)
        self._audit.record(
            "technician_updated",
            actor_id=actor_id,
            entity_type="Technician",
            entity_id=tech.id,
            entity_uuid=tech.uuid,
        )
        return tech

    def delete_technician(self, technician_id: int, *, actor_id: int | None = None) -> None:
        tech = self.get_technician(technician_id)
        self._technicians.soft_delete(tech, actor_id=actor_id)
        self._audit.record(
            "technician_deleted",
            actor_id=actor_id,
            entity_type="Technician",
            entity_id=tech.id,
            entity_uuid=tech.uuid,
        )

    def assign_to_work_order(
        self,
        work_order_id: int,
        technician_id: int | None,
        *,
        actor_id: int | None = None,
    ) -> None:
        work_order = self._work_orders.require_by_id(work_order_id)
        if technician_id is not None:
            tech = self.get_technician(technician_id)
            if tech.company_id != work_order.company_id:
                raise ValidationError("Texnik kompaniyaga mos emas.")
            if not tech.is_active:
                raise ValidationError("Texnik faol emas.")
            work_order.technician_id = tech.id
        else:
            work_order.technician_id = None
        work_order.updated_by = actor_id
        self._work_orders.save(work_order)
        if technician_id is not None:
            event = WorkOrderTimelineEvent(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                event_code=EVENT_TECHNICIAN_ASSIGNED,
                visibility=VISIBILITY_STAFF,
                title=event_label(EVENT_TECHNICIAN_ASSIGNED),
                notes=f"technician_id={technician_id}",
                actor_id=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
            self._session.add(event)
            self._session.flush()
        self._audit.record(
            "work_order_technician_assigned",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=str(technician_id),
        )
