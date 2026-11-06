"""Customer application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.customers.models.customer import Customer
from app.modules.customers.models.device import Device
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.customers.repositories.device_repository import DeviceRepository
from app.modules.customers.schemas.customer_schema import (
    CustomerCreateSchema,
    CustomerUpdateSchema,
    DeviceCreateSchema,
    DeviceUpdateSchema,
)
from app.services.audit_service import AuditService


class CustomerService:
    """Use cases for customers and their devices."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._devices = DeviceRepository(session)
        self._audit = AuditService(session)

    def list_customers(self, company_id: int, *, query: str | None = None) -> list[Customer]:
        """Return customers for a company, optionally filtered."""
        return self._customers.search(company_id, query=query)

    def get_customer(self, customer_id: int) -> Customer:
        """Return a customer with devices or raise."""
        customer = self._customers.get_with_devices(customer_id)
        if customer is None:
            raise NotFoundError("Mijoz topilmadi.", entity="Customer")
        return customer

    def create_customer(
        self,
        company_id: int,
        payload: CustomerCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Customer:
        """Create a new customer."""
        existing = self._customers.get_by_phone(
            company_id, payload.phone, include_deleted=True
        )
        if existing is not None:
            if existing.deleted_at is not None:
                existing.restore(actor_id=actor_id)
                existing.display_name = payload.display_name
                existing.phone = payload.phone
                existing.email = payload.email
                existing.address = payload.address
                existing.notes = payload.notes
                existing.customer_type = payload.customer_type
                existing.tax_id = payload.tax_id
                existing.is_active = True
                existing.updated_by = actor_id
                self._customers.save(existing)
                self._audit.record(
                    "customer_restored",
                    actor_id=actor_id,
                    entity_type="Customer",
                    entity_id=existing.id,
                    entity_uuid=existing.uuid,
                    message=existing.display_name,
                )
                return existing
            raise ConflictError(f"Bu telefon allaqachon mavjud: {payload.phone}")

        customer = Customer(
            company_id=company_id,
            display_name=payload.display_name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            notes=payload.notes,
            customer_type=payload.customer_type,
            tax_id=payload.tax_id,
            created_by=actor_id,
            updated_by=actor_id,
        )
        try:
            self._customers.add(customer)
        except Exception as exc:  # noqa: BLE001 — map DB unique to domain error
            if "UNIQUE" in str(exc).upper() or "unique" in str(exc).lower():
                raise ConflictError(f"Bu telefon allaqachon mavjud: {payload.phone}") from exc
            raise
        self._audit.record(
            "customer_created",
            actor_id=actor_id,
            entity_type="Customer",
            entity_id=customer.id,
            entity_uuid=customer.uuid,
            message=customer.display_name,
        )
        return customer

    def update_customer(
        self,
        customer_id: int,
        payload: CustomerUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Customer:
        """Update an existing customer."""
        customer = self.get_customer(customer_id)
        duplicate = self._customers.get_by_phone(customer.company_id, payload.phone)
        if duplicate is not None and duplicate.id != customer.id:
            raise ConflictError(f"Bu telefon allaqachon mavjud: {payload.phone}")

        customer.display_name = payload.display_name
        customer.phone = payload.phone
        customer.email = payload.email
        customer.address = payload.address
        customer.notes = payload.notes
        customer.customer_type = payload.customer_type
        customer.tax_id = payload.tax_id
        customer.is_active = payload.is_active
        customer.is_blacklisted = payload.is_blacklisted
        customer.updated_by = actor_id
        self._customers.save(customer)
        self._audit.record(
            "customer_updated",
            actor_id=actor_id,
            entity_type="Customer",
            entity_id=customer.id,
            entity_uuid=customer.uuid,
        )
        return customer

    def delete_customer(self, customer_id: int, *, actor_id: int | None = None) -> None:
        """Soft-delete a customer and their devices."""
        customer = self.get_customer(customer_id)
        for device in list(customer.devices):
            if device.deleted_at is None:
                self._devices.soft_delete(device, actor_id=actor_id)
        self._customers.soft_delete(customer, actor_id=actor_id)
        self._audit.record(
            "customer_deleted",
            actor_id=actor_id,
            entity_type="Customer",
            entity_id=customer.id,
            entity_uuid=customer.uuid,
        )

    def create_device(
        self,
        customer_id: int,
        payload: DeviceCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Device:
        """Register a device for a customer."""
        customer = self.get_customer(customer_id)
        self._ensure_unique_device_ids(
            customer.company_id,
            imei=payload.imei,
            serial_number=payload.serial_number,
        )
        device = Device(
            company_id=customer.company_id,
            customer_id=customer.id,
            device_type=payload.device_type,
            brand=payload.brand,
            model=payload.model,
            serial_number=payload.serial_number,
            imei=payload.imei,
            color=payload.color,
            notes=payload.notes,
            access_code=payload.access_code,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._devices.add(device)
        self._audit.record(
            "device_created",
            actor_id=actor_id,
            entity_type="Device",
            entity_id=device.id,
            entity_uuid=device.uuid,
            message=device.display_label,
        )
        return device

    def update_device(
        self,
        device_id: int,
        payload: DeviceUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Device:
        """Update device details."""
        device = self._devices.require_by_id(device_id)
        self._ensure_unique_device_ids(
            device.company_id,
            imei=payload.imei,
            serial_number=payload.serial_number,
            exclude_id=device.id,
        )
        device.device_type = payload.device_type
        device.brand = payload.brand
        device.model = payload.model
        device.serial_number = payload.serial_number
        device.imei = payload.imei
        device.color = payload.color
        device.notes = payload.notes
        device.access_code = payload.access_code
        device.updated_by = actor_id
        self._devices.save(device)
        self._audit.record(
            "device_updated",
            actor_id=actor_id,
            entity_type="Device",
            entity_id=device.id,
            entity_uuid=device.uuid,
        )
        return device

    def delete_device(self, device_id: int, *, actor_id: int | None = None) -> None:
        """Soft-delete a device."""
        device = self._devices.require_by_id(device_id)
        self._devices.soft_delete(device, actor_id=actor_id)
        self._audit.record(
            "device_deleted",
            actor_id=actor_id,
            entity_type="Device",
            entity_id=device.id,
            entity_uuid=device.uuid,
        )

    def _ensure_unique_device_ids(
        self,
        company_id: int,
        *,
        imei: str | None,
        serial_number: str | None,
        exclude_id: int | None = None,
    ) -> None:
        found = self._devices.find_by_identifier(
            company_id,
            imei=imei,
            serial_number=serial_number,
        )
        if found is not None and found.id != exclude_id:
            raise ConflictError("IMEI yoki seriya raqami allaqachon roʻyxatda bor.")
