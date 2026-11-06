"""B2B business client service."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.business_clients.models.business_client import (
    BusinessClient,
    BusinessClientContact,
)
from app.modules.business_clients.repositories.business_client_repository import (
    BusinessClientContactRepository,
    BusinessClientRepository,
)
from app.modules.business_clients.schemas.business_client_schema import (
    BusinessClientCreateSchema,
    BusinessClientUpdateSchema,
    ContactCreateSchema,
)
from app.modules.customers.models.customer import Customer
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.services.audit_service import AuditService


class BusinessClientService:
    """CRUD for B2B companies, contacts, customer links, credit hold."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._clients = BusinessClientRepository(session)
        self._contacts = BusinessClientContactRepository(session)
        self._customers = CustomerRepository(session)
        self._audit = AuditService(session)

    def list_clients(self, company_id: int, *, query: str | None = None) -> list[BusinessClient]:
        return self._clients.search(company_id, query=query)

    def get_client(self, client_id: int) -> BusinessClient:
        client = self._clients.get_with_contacts(client_id)
        if client is None:
            raise NotFoundError("B2B kompaniya topilmadi.", entity="BusinessClient")
        return client

    def create_client(
        self,
        company_id: int,
        payload: BusinessClientCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> BusinessClient:
        existing = self._session.scalar(
            select(BusinessClient).where(
                BusinessClient.company_id == company_id,
                BusinessClient.name == payload.name,
                BusinessClient.deleted_at.is_(None),
            )
        )
        if existing is not None:
            raise ConflictError(f"Bu nom allaqachon mavjud: {payload.name}")
        client = BusinessClient(
            company_id=company_id,
            name=payload.name,
            tax_id=payload.tax_id,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            credit_limit=payload.credit_limit or Decimal("0"),
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._clients.add(client)
        self._audit.record(
            "business_client_created",
            actor_id=actor_id,
            entity_type="BusinessClient",
            entity_id=client.id,
            entity_uuid=client.uuid,
            message=client.name,
        )
        return client

    def update_client(
        self,
        client_id: int,
        payload: BusinessClientUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> BusinessClient:
        client = self.get_client(client_id)
        client.name = payload.name
        client.tax_id = payload.tax_id
        client.phone = payload.phone
        client.email = payload.email
        client.address = payload.address
        client.credit_limit = payload.credit_limit or Decimal("0")
        client.credit_hold = payload.credit_hold
        client.is_active = payload.is_active
        client.notes = payload.notes
        client.updated_by = actor_id
        self._clients.save(client)
        self._audit.record(
            "business_client_updated",
            actor_id=actor_id,
            entity_type="BusinessClient",
            entity_id=client.id,
            entity_uuid=client.uuid,
        )
        return client

    def set_credit_hold(
        self,
        client_id: int,
        hold: bool,
        *,
        actor_id: int | None = None,
    ) -> BusinessClient:
        client = self.get_client(client_id)
        client.credit_hold = hold
        client.updated_by = actor_id
        self._clients.save(client)
        self._audit.record(
            "business_client_credit_hold" if hold else "business_client_credit_release",
            actor_id=actor_id,
            entity_type="BusinessClient",
            entity_id=client.id,
            entity_uuid=client.uuid,
        )
        return client

    def soft_delete_client(self, client_id: int, *, actor_id: int | None = None) -> None:
        client = self.get_client(client_id)
        client.soft_delete(actor_id=actor_id)
        self._clients.save(client)
        self._audit.record(
            "business_client_deleted",
            actor_id=actor_id,
            entity_type="BusinessClient",
            entity_id=client.id,
            entity_uuid=client.uuid,
        )

    def add_contact(
        self,
        client_id: int,
        payload: ContactCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> BusinessClientContact:
        client = self.get_client(client_id)
        contact = BusinessClientContact(
            company_id=client.company_id,
            business_client_id=client.id,
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            job_title=payload.job_title,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._contacts.add(contact)
        self._audit.record(
            "business_contact_created",
            actor_id=actor_id,
            entity_type="BusinessClientContact",
            entity_id=contact.id,
            entity_uuid=contact.uuid,
        )
        return contact

    def delete_contact(self, contact_id: int, *, actor_id: int | None = None) -> None:
        contact = self._contacts.get_by_id(contact_id)
        if contact is None:
            raise NotFoundError("Kontakt topilmadi.", entity="BusinessClientContact")
        contact.soft_delete(actor_id=actor_id)
        self._contacts.save(contact)

    def list_linked_customers(self, client_id: int) -> list[Customer]:
        client = self.get_client(client_id)
        stmt = (
            select(Customer)
            .where(
                Customer.company_id == client.company_id,
                Customer.business_client_id == client_id,
                Customer.deleted_at.is_(None),
            )
            .order_by(Customer.display_name)
        )
        return list(self._session.scalars(stmt))

    def link_customer(
        self,
        client_id: int,
        customer_id: int,
        *,
        actor_id: int | None = None,
    ) -> Customer:
        client = self.get_client(client_id)
        customer = self._customers.get_by_id(customer_id)
        if customer is None or customer.company_id != client.company_id:
            raise NotFoundError("Mijoz topilmadi.", entity="Customer")
        if client.credit_hold:
            raise ValidationError("Kredit toʻxtatilgan — yangi bogʻlash mumkin emas.")
        customer.business_client_id = client.id
        customer.customer_type = "business"
        customer.updated_by = actor_id
        self._customers.save(customer)
        self._audit.record(
            "customer_linked_business",
            actor_id=actor_id,
            entity_type="Customer",
            entity_id=customer.id,
            entity_uuid=customer.uuid,
            message=f"business_client={client.id}",
        )
        return customer

    def unlink_customer(
        self,
        customer_id: int,
        *,
        actor_id: int | None = None,
    ) -> Customer:
        customer = self._customers.get_by_id(customer_id)
        if customer is None:
            raise NotFoundError("Mijoz topilmadi.", entity="Customer")
        customer.business_client_id = None
        customer.updated_by = actor_id
        self._customers.save(customer)
        return customer
