"""Branch repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.branches.models.branch import Branch
from app.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    model = Branch

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_code(self, company_id: int, code: str) -> Branch | None:
        stmt = self._base_query().where(
            Branch.company_id == company_id,
            Branch.code == code,
        )
        return self._session.scalar(stmt)

    def get_default(self, company_id: int) -> Branch | None:
        stmt = self._base_query().where(
            Branch.company_id == company_id,
            Branch.is_default.is_(True),
            Branch.is_active.is_(True),
        )
        return self._session.scalar(stmt)

    def list_active(self, company_id: int) -> list[Branch]:
        stmt = (
            self._base_query()
            .where(Branch.company_id == company_id, Branch.is_active.is_(True))
            .order_by(Branch.name)
        )
        return list(self._session.scalars(stmt))
