"""Company repository."""

from __future__ import annotations

from app.modules.companies.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Persistence operations for companies."""

    model = Company

    def get_by_code(self, code: str) -> Company | None:
        """Return a company by unique code."""
        stmt = self._base_query().where(Company.code == code)
        return self._session.scalar(stmt)

    def list_active(self) -> list[Company]:
        """Return active companies ordered by name."""
        stmt = (
            self._base_query()
            .where(Company.is_active.is_(True))
            .order_by(Company.name)
        )
        return list(self._session.scalars(stmt))

    def get_default(self) -> Company | None:
        """Return the first active company (bootstrap helper)."""
        companies = self.list_active()
        return companies[0] if companies else None
