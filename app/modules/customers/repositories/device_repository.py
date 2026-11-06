"""Device repository."""

from __future__ import annotations

from sqlalchemy import or_

from app.modules.customers.models.device import Device
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    """Persistence for devices."""

    model = Device

    def list_by_customer(self, customer_id: int) -> list[Device]:
        """Return active devices for a customer."""
        stmt = (
            self._base_query()
            .where(Device.customer_id == customer_id)
            .order_by(Device.model)
        )
        return list(self._session.scalars(stmt))

    def find_by_identifier(
        self,
        company_id: int,
        *,
        imei: str | None = None,
        serial_number: str | None = None,
    ) -> Device | None:
        """Find device by IMEI or serial number within company."""
        if not imei and not serial_number:
            return None
        conditions = []
        if imei:
            conditions.append(Device.imei == imei)
        if serial_number:
            conditions.append(Device.serial_number == serial_number)
        stmt = self._base_query().where(
            Device.company_id == company_id,
            or_(*conditions),
        )
        return self._session.scalar(stmt)
