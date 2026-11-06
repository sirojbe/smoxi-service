"""Business client repository."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.modules.business_clients.models.business_client import (
    BusinessClient,
    BusinessClientContact,
)
from app.repositories.base import BaseRepository


class BusinessClientRepository(BaseRepository[BusinessClient]):
    model = BusinessClient

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def search(self, company_id: int, *, query: str | None = None) -> list[BusinessClient]:
        stmt = (
            self._base_query()
            .where(BusinessClient.company_id == company_id)
            .options(joinedload(BusinessClient.contacts))
            .order_by(BusinessClient.name)
        )
        if query:
            q = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    BusinessClient.name.ilike(q),
                    BusinessClient.tax_id.ilike(q),
                    BusinessClient.phone.ilike(q),
                    BusinessClient.email.ilike(q),
                )
            )
        return list(self._session.scalars(stmt).unique())

    def get_with_contacts(self, client_id: int) -> BusinessClient | None:
        stmt = (
            select(BusinessClient)
            .where(BusinessClient.id == client_id, BusinessClient.deleted_at.is_(None))
            .options(joinedload(BusinessClient.contacts))
        )
        return self._session.scalar(stmt)


class BusinessClientContactRepository(BaseRepository[BusinessClientContact]):
    model = BusinessClientContact

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_client(self, client_id: int) -> list[BusinessClientContact]:
        stmt = (
            self._base_query()
            .where(BusinessClientContact.business_client_id == client_id)
            .order_by(BusinessClientContact.full_name)
        )
        return list(self._session.scalars(stmt))
