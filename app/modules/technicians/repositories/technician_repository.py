"""Technician repository."""

from __future__ import annotations

from sqlalchemy import or_

from app.modules.technicians.models.technician import Technician
from app.repositories.base import BaseRepository


class TechnicianRepository(BaseRepository[Technician]):
    """Persistence for technicians."""

    model = Technician

    def get_by_code(self, company_id: int, code: str) -> Technician | None:
        stmt = self._base_query().where(
            Technician.company_id == company_id,
            Technician.code == code,
        )
        return self._session.scalar(stmt)

    def search(self, company_id: int, *, query: str | None = None) -> list[Technician]:
        stmt = (
            self._base_query()
            .where(Technician.company_id == company_id)
            .order_by(Technician.full_name)
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Technician.full_name.ilike(pattern),
                    Technician.code.ilike(pattern),
                    Technician.phone.ilike(pattern),
                    Technician.skills.ilike(pattern),
                )
            )
        return list(self._session.scalars(stmt))

    def list_available(self, company_id: int) -> list[Technician]:
        stmt = (
            self._base_query()
            .where(
                Technician.company_id == company_id,
                Technician.is_active.is_(True),
                Technician.is_available.is_(True),
            )
            .order_by(Technician.full_name)
        )
        return list(self._session.scalars(stmt))
