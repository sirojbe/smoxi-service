"""Supplier and purchasing application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.time import utc_now
from app.modules.inventory.models.enums import StockMovementType
from app.modules.inventory.repositories.item_repository import InventoryItemRepository
from app.modules.inventory.repositories.warehouse_repository import WarehouseRepository
from app.modules.inventory.schemas.item_schema import StockAdjustSchema
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.suppliers.models.enums import PurchaseOrderStatus
from app.modules.suppliers.models.supplier import PurchaseOrder, PurchaseOrderLine, Supplier
from app.modules.suppliers.repositories.supplier_repository import (
    PurchaseOrderRepository,
    SupplierRepository,
)
from app.modules.suppliers.schemas.supplier_schema import (
    PurchaseOrderCreateSchema,
    SupplierCreateSchema,
    SupplierUpdateSchema,
)
from app.services.audit_service import AuditService


class SupplierService:
    """Suppliers and purchase order use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._suppliers = SupplierRepository(session)
        self._orders = PurchaseOrderRepository(session)
        self._items = InventoryItemRepository(session)
        self._warehouses = WarehouseRepository(session)
        self._inventory = InventoryService(session)
        self._audit = AuditService(session)

    def list_suppliers(self, company_id: int, *, query: str | None = None) -> list[Supplier]:
        return self._suppliers.search(company_id, query=query)

    def get_supplier(self, supplier_id: int) -> Supplier:
        supplier = self._suppliers.get_by_id(supplier_id)
        if supplier is None:
            raise NotFoundError("Yetkazib beruvchi topilmadi.", entity="Supplier")
        return supplier

    def create_supplier(
        self,
        company_id: int,
        payload: SupplierCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Supplier:
        if self._suppliers.get_by_code(company_id, payload.code) is not None:
            raise ConflictError(f"Kod allaqachon mavjud: {payload.code}")
        supplier = Supplier(
            company_id=company_id,
            code=payload.code,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._suppliers.add(supplier)
        self._audit.record(
            "supplier_created",
            actor_id=actor_id,
            entity_type="Supplier",
            entity_id=supplier.id,
            entity_uuid=supplier.uuid,
            message=supplier.name,
        )
        return supplier

    def update_supplier(
        self,
        supplier_id: int,
        payload: SupplierUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Supplier:
        supplier = self.get_supplier(supplier_id)
        duplicate = self._suppliers.get_by_code(supplier.company_id, payload.code)
        if duplicate is not None and duplicate.id != supplier.id:
            raise ConflictError(f"Kod allaqachon mavjud: {payload.code}")
        supplier.code = payload.code
        supplier.name = payload.name
        supplier.phone = payload.phone
        supplier.email = payload.email
        supplier.address = payload.address
        supplier.notes = payload.notes
        supplier.is_active = payload.is_active
        supplier.updated_by = actor_id
        self._suppliers.save(supplier)
        self._audit.record(
            "supplier_updated",
            actor_id=actor_id,
            entity_type="Supplier",
            entity_id=supplier.id,
            entity_uuid=supplier.uuid,
        )
        return supplier

    def delete_supplier(self, supplier_id: int, *, actor_id: int | None = None) -> None:
        supplier = self.get_supplier(supplier_id)
        self._suppliers.soft_delete(supplier, actor_id=actor_id)
        self._audit.record(
            "supplier_deleted",
            actor_id=actor_id,
            entity_type="Supplier",
            entity_id=supplier.id,
            entity_uuid=supplier.uuid,
        )

    def list_purchase_orders(self, company_id: int) -> list[PurchaseOrder]:
        return self._orders.list_for_company(company_id)

    def get_purchase_order(self, purchase_order_id: int) -> PurchaseOrder:
        order = self._orders.get_with_lines(purchase_order_id)
        if order is None:
            raise NotFoundError("Xarid buyurtmasi topilmadi.", entity="PurchaseOrder")
        return order

    def create_purchase_order(
        self,
        company_id: int,
        payload: PurchaseOrderCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> PurchaseOrder:
        supplier = self.get_supplier(payload.supplier_id)
        if supplier.company_id != company_id or not supplier.is_active:
            raise ValidationError("Yetkazib beruvchi yaroqsiz.")

        if payload.warehouse_id is not None:
            warehouse = self._warehouses.get_by_id(payload.warehouse_id)
            if warehouse is None or warehouse.company_id != company_id:
                raise ValidationError("Ombor topilmadi.")
        else:
            warehouse = self._inventory.ensure_default_warehouse(company_id, actor_id=actor_id)

        total = 0
        for line in payload.lines:
            item = self._items.get_by_id(line.inventory_item_id)
            if item is None or item.company_id != company_id:
                raise ValidationError("Ombor tovari topilmadi.")
            total += line.quantity * line.unit_cost

        number = self._generate_number(company_id)
        status = (
            PurchaseOrderStatus.ORDERED if payload.submit else PurchaseOrderStatus.DRAFT
        )
        order = PurchaseOrder(
            company_id=company_id,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            number=number,
            status=status.value,
            notes=payload.notes,
            total_amount=total,
            ordered_at=utc_now() if payload.submit else None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._orders.add(order)
        for line in payload.lines:
            order.lines.append(
                PurchaseOrderLine(
                    inventory_item_id=line.inventory_item_id,
                    quantity=line.quantity,
                    unit_cost=line.unit_cost,
                    line_total=line.quantity * line.unit_cost,
                )
            )
        self._session.flush()
        self._audit.record(
            "purchase_order_created",
            actor_id=actor_id,
            entity_type="PurchaseOrder",
            entity_id=order.id,
            entity_uuid=order.uuid,
            message=order.number,
        )
        return order

    def receive_purchase_order(
        self,
        purchase_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> PurchaseOrder:
        """Receive PO and increase inventory stock."""
        order = self.get_purchase_order(purchase_order_id)
        if order.status == PurchaseOrderStatus.RECEIVED.value:
            raise ValidationError("Buyurtma allaqachon qabul qilingan.")
        if order.status == PurchaseOrderStatus.CANCELLED.value:
            raise ValidationError("Bekor qilingan buyurtmani qabul qilib boʻlmaydi.")
        if order.status == PurchaseOrderStatus.DRAFT.value:
            order.status = PurchaseOrderStatus.ORDERED.value
            order.ordered_at = utc_now()

        for line in order.lines:
            self._inventory.adjust_stock(
                line.inventory_item_id,
                StockAdjustSchema(
                    movement_type=StockMovementType.IN.value,
                    quantity=line.quantity,
                    reason=f"Xarid {order.number}",
                    reference=order.number,
                ),
                actor_id=actor_id,
            )

        order.status = PurchaseOrderStatus.RECEIVED.value
        order.received_at = utc_now()
        order.updated_by = actor_id
        self._orders.save(order)
        self._audit.record(
            "purchase_order_received",
            actor_id=actor_id,
            entity_type="PurchaseOrder",
            entity_id=order.id,
            entity_uuid=order.uuid,
            message=order.number,
        )
        return order

    def cancel_purchase_order(
        self,
        purchase_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> PurchaseOrder:
        order = self.get_purchase_order(purchase_order_id)
        if order.status == PurchaseOrderStatus.RECEIVED.value:
            raise ValidationError("Qabul qilingan buyurtmani bekor qilib boʻlmaydi.")
        if order.status == PurchaseOrderStatus.CANCELLED.value:
            raise ValidationError("Buyurtma allaqachon bekor qilingan.")
        order.status = PurchaseOrderStatus.CANCELLED.value
        order.updated_by = actor_id
        self._orders.save(order)
        self._audit.record(
            "purchase_order_cancelled",
            actor_id=actor_id,
            entity_type="PurchaseOrder",
            entity_id=order.id,
            entity_uuid=order.uuid,
        )
        return order

    def _generate_number(self, company_id: int) -> str:
        today = utc_now().strftime("%Y%m%d")
        prefix = f"PO-{today}-"
        seq = self._orders.next_sequence(company_id, prefix)
        return f"{prefix}{seq:04d}"
