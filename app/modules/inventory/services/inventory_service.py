"""Inventory application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.inventory.models.enums import StockMovementType
from app.modules.inventory.models.item import InventoryItem, StockMovement
from app.modules.inventory.models.warehouse import Warehouse
from app.modules.inventory.repositories.item_repository import InventoryItemRepository
from app.modules.inventory.repositories.warehouse_repository import WarehouseRepository
from app.modules.inventory.schemas.item_schema import (
    InventoryItemCreateSchema,
    InventoryItemUpdateSchema,
    StockAdjustSchema,
)
from app.services.audit_service import AuditService

DEFAULT_WAREHOUSE_CODE = "main"
DEFAULT_WAREHOUSE_NAME = "Asosiy ombor"


class InventoryService:
    """Use cases for warehouses, items, and stock movements."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._items = InventoryItemRepository(session)
        self._warehouses = WarehouseRepository(session)
        self._audit = AuditService(session)

    def ensure_default_warehouse(self, company_id: int, *, actor_id: int | None = None) -> Warehouse:
        """Create a default warehouse if the company has none."""
        existing = self._warehouses.get_default(company_id)
        if existing is not None:
            return existing
        by_code = self._warehouses.get_by_code(company_id, DEFAULT_WAREHOUSE_CODE)
        if by_code is not None:
            by_code.is_default = True
            return self._warehouses.save(by_code)
        warehouse = Warehouse(
            company_id=company_id,
            code=DEFAULT_WAREHOUSE_CODE,
            name=DEFAULT_WAREHOUSE_NAME,
            is_default=True,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self._warehouses.add(warehouse)

    def list_items(
        self,
        company_id: int,
        *,
        query: str | None = None,
        low_stock_only: bool = False,
    ) -> list[InventoryItem]:
        """Return inventory items."""
        self.ensure_default_warehouse(company_id)
        return self._items.search(
            company_id,
            query=query,
            low_stock_only=low_stock_only,
        )

    def get_item(self, item_id: int) -> InventoryItem:
        """Return an inventory item or raise."""
        item = self._items.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Tovar topilmadi.", entity="InventoryItem")
        return item

    def create_item(
        self,
        company_id: int,
        payload: InventoryItemCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> InventoryItem:
        """Create a new inventory item."""
        warehouse = None
        if payload.warehouse_id is not None:
            warehouse = self._warehouses.get_by_id(payload.warehouse_id)
            if warehouse is None or warehouse.company_id != company_id:
                raise ValidationError("Ombor topilmadi.")
        else:
            warehouse = self.ensure_default_warehouse(company_id, actor_id=actor_id)

        if self._items.get_by_sku_warehouse(company_id, payload.sku, warehouse.id) is not None:
            raise ConflictError(f"SKU allaqachon mavjud: {payload.sku}")

        item = InventoryItem(
            company_id=company_id,
            warehouse_id=warehouse.id,
            sku=payload.sku,
            name=payload.name,
            category=payload.category,
            barcode=payload.barcode,
            unit=payload.unit,
            quantity_on_hand=payload.quantity_on_hand,
            min_quantity=payload.min_quantity,
            purchase_price=payload.purchase_price,
            sale_price=payload.sale_price,
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._items.add(item)
        if payload.quantity_on_hand > 0:
            self._items.add_movement(
                StockMovement(
                    company_id=company_id,
                    item_id=item.id,
                    warehouse_id=warehouse.id,
                    movement_type=StockMovementType.IN.value,
                    quantity_delta=payload.quantity_on_hand,
                    quantity_after=payload.quantity_on_hand,
                    reason="Boshlangʻich zaxira",
                    moved_by=actor_id,
                )
            )
        self._audit.record(
            "inventory_item_created",
            actor_id=actor_id,
            entity_type="InventoryItem",
            entity_id=item.id,
            entity_uuid=item.uuid,
            message=item.sku,
        )
        return item

    def update_item(
        self,
        item_id: int,
        payload: InventoryItemUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> InventoryItem:
        """Update item master data (not stock quantity)."""
        item = self.get_item(item_id)
        duplicate = self._items.get_by_sku(item.company_id, payload.sku)
        if duplicate is not None and duplicate.id != item.id:
            raise ConflictError(f"SKU allaqachon mavjud: {payload.sku}")

        item.sku = payload.sku
        item.name = payload.name
        item.category = payload.category
        item.barcode = payload.barcode
        item.unit = payload.unit
        item.min_quantity = payload.min_quantity
        item.purchase_price = payload.purchase_price
        item.sale_price = payload.sale_price
        item.notes = payload.notes
        item.is_active = payload.is_active
        item.updated_by = actor_id
        self._items.save(item)
        self._audit.record(
            "inventory_item_updated",
            actor_id=actor_id,
            entity_type="InventoryItem",
            entity_id=item.id,
            entity_uuid=item.uuid,
        )
        return item

    def delete_item(self, item_id: int, *, actor_id: int | None = None) -> None:
        """Soft-delete an inventory item."""
        item = self.get_item(item_id)
        self._items.soft_delete(item, actor_id=actor_id)
        self._audit.record(
            "inventory_item_deleted",
            actor_id=actor_id,
            entity_type="InventoryItem",
            entity_id=item.id,
            entity_uuid=item.uuid,
        )

    def adjust_stock(
        self,
        item_id: int,
        payload: StockAdjustSchema,
        *,
        actor_id: int | None = None,
    ) -> InventoryItem:
        """Apply an in/out/adjust stock movement."""
        item = self.get_item(item_id)
        movement_type = StockMovementType(payload.movement_type)

        if movement_type == StockMovementType.IN:
            if payload.quantity < 1:
                raise ValidationError("Kirim miqdori kamida 1 boʻlishi kerak.")
            delta = payload.quantity
        elif movement_type == StockMovementType.OUT:
            if payload.quantity < 1:
                raise ValidationError("Chiqim miqdori kamida 1 boʻlishi kerak.")
            delta = -payload.quantity
        else:
            delta = payload.quantity - item.quantity_on_hand
            if delta == 0:
                raise ValidationError("Zaxira oʻzgarmadi.")

        new_qty = item.quantity_on_hand + delta
        if new_qty < 0:
            raise ValidationError("Zaxira manfiy boʻlishi mumkin emas.")

        item.quantity_on_hand = new_qty
        item.updated_by = actor_id
        self._items.save(item)
        self._items.add_movement(
            StockMovement(
                company_id=item.company_id,
                item_id=item.id,
                warehouse_id=item.warehouse_id,
                movement_type=movement_type.value,
                quantity_delta=delta,
                quantity_after=new_qty,
                reason=payload.reason,
                reference=payload.reference,
                moved_by=actor_id,
            )
        )
        self._audit.record(
            "inventory_stock_adjusted",
            actor_id=actor_id,
            entity_type="InventoryItem",
            entity_id=item.id,
            entity_uuid=item.uuid,
            message=f"{movement_type.value}:{delta}",
        )
        if new_qty <= item.min_quantity:
            try:
                from app.modules.notifications.services.notification_service import (
                    NotificationService,
                )

                NotificationService(self._session).notify_low_stock(
                    item.company_id,
                    item_name=item.name,
                    quantity=new_qty,
                    item_id=item.id,
                    actor_id=actor_id,
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                from app.modules.automation.services.automation_service import (
                    AutomationService,
                )

                AutomationService(self._session).fire_trigger(
                    item.company_id,
                    "low_stock",
                    context=f"{item.name}={new_qty}",
                    actor_id=actor_id,
                )
            except Exception:  # noqa: BLE001
                pass
        return item

    def list_movements(self, item_id: int) -> list[StockMovement]:
        """Return movement history for an item."""
        self.get_item(item_id)
        return self._items.list_movements(item_id)

    def list_warehouses(self, company_id: int) -> list[Warehouse]:
        """Return active warehouses (ensures default exists)."""
        self.ensure_default_warehouse(company_id)
        return self._warehouses.list_active(company_id)

    def create_warehouse(
        self,
        company_id: int,
        *,
        code: str,
        name: str,
        address: str | None = None,
        is_default: bool = False,
        actor_id: int | None = None,
    ) -> Warehouse:
        code = code.strip().upper()
        name = name.strip()
        if not code or not name:
            raise ValidationError("Ombor kodi va nomi majburiy.")
        if self._warehouses.get_by_code(company_id, code) is not None:
            raise ConflictError(f"Ombor kodi band: {code}")
        if is_default:
            self._clear_default_warehouse(company_id)
        warehouse = Warehouse(
            company_id=company_id,
            code=code,
            name=name,
            address=address,
            is_default=is_default,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._warehouses.add(warehouse)
        self._audit.record(
            "warehouse_created",
            actor_id=actor_id,
            entity_type="Warehouse",
            entity_id=warehouse.id,
            entity_uuid=warehouse.uuid,
            message=code,
        )
        return warehouse

    def update_warehouse(
        self,
        warehouse_id: int,
        *,
        code: str,
        name: str,
        address: str | None = None,
        is_default: bool = False,
        is_active: bool = True,
        actor_id: int | None = None,
    ) -> Warehouse:
        warehouse = self._warehouses.get_by_id(warehouse_id)
        if warehouse is None:
            raise NotFoundError("Ombor topilmadi.", entity="Warehouse")
        code = code.strip().upper()
        name = name.strip()
        other = self._warehouses.get_by_code(warehouse.company_id, code)
        if other is not None and other.id != warehouse.id:
            raise ConflictError(f"Ombor kodi band: {code}")
        if is_default:
            self._clear_default_warehouse(warehouse.company_id)
        if not is_active and warehouse.is_default:
            raise ValidationError("Asosiy omborni nofaol qilib boʻlmaydi.")
        warehouse.code = code
        warehouse.name = name
        warehouse.address = address
        warehouse.is_default = is_default
        warehouse.is_active = is_active
        warehouse.updated_by = actor_id
        self._warehouses.save(warehouse)
        self._audit.record(
            "warehouse_updated",
            actor_id=actor_id,
            entity_type="Warehouse",
            entity_id=warehouse.id,
            entity_uuid=warehouse.uuid,
        )
        return warehouse

    def soft_delete_warehouse(
        self,
        warehouse_id: int,
        *,
        actor_id: int | None = None,
    ) -> None:
        warehouse = self._warehouses.get_by_id(warehouse_id)
        if warehouse is None:
            raise NotFoundError("Ombor topilmadi.", entity="Warehouse")
        if warehouse.is_default:
            raise ValidationError("Asosiy omborni oʻchirib boʻlmaydi.")
        warehouse.soft_delete(actor_id=actor_id)
        self._warehouses.save(warehouse)
        self._audit.record(
            "warehouse_deleted",
            actor_id=actor_id,
            entity_type="Warehouse",
            entity_id=warehouse.id,
            entity_uuid=warehouse.uuid,
        )

    def transfer_stock(
        self,
        item_id: int,
        *,
        to_warehouse_id: int,
        quantity: int,
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> InventoryItem:
        """Move stock from item's warehouse to another warehouse."""
        if quantity < 1:
            raise ValidationError("Oʻtkazma miqdori kamida 1 boʻlishi kerak.")
        source = self.get_item(item_id)
        if source.warehouse_id == to_warehouse_id:
            raise ValidationError("Manba va maqsad ombor bir xil.")
        dest_wh = self._warehouses.get_by_id(to_warehouse_id)
        if dest_wh is None or dest_wh.company_id != source.company_id:
            raise NotFoundError("Maqsad ombor topilmadi.", entity="Warehouse")
        if not dest_wh.is_active:
            raise ValidationError("Maqsad ombor faol emas.")
        if quantity > source.quantity_on_hand:
            raise ValidationError("Zaxira yetarli emas.")

        ref = f"TR:{source.warehouse_id}->{to_warehouse_id}"
        if quantity == source.quantity_on_hand:
            old_wh = source.warehouse_id
            source.warehouse_id = to_warehouse_id
            source.updated_by = actor_id
            self._items.save(source)
            self._items.add_movement(
                StockMovement(
                    company_id=source.company_id,
                    item_id=source.id,
                    warehouse_id=to_warehouse_id,
                    movement_type=StockMovementType.TRANSFER.value,
                    quantity_delta=0,
                    quantity_after=source.quantity_on_hand,
                    reason=reason or f"Ombor koʻchirish {old_wh}->{to_warehouse_id}",
                    reference=ref,
                    moved_by=actor_id,
                )
            )
            self._audit.record(
                "inventory_transferred",
                actor_id=actor_id,
                entity_type="InventoryItem",
                entity_id=source.id,
                entity_uuid=source.uuid,
                message=ref,
            )
            return source

        source.quantity_on_hand -= quantity
        source.updated_by = actor_id
        self._items.save(source)
        self._items.add_movement(
            StockMovement(
                company_id=source.company_id,
                item_id=source.id,
                warehouse_id=source.warehouse_id,
                movement_type=StockMovementType.TRANSFER.value,
                quantity_delta=-quantity,
                quantity_after=source.quantity_on_hand,
                reason=reason or "Omborlararo chiqim",
                reference=ref,
                moved_by=actor_id,
            )
        )

        dest = self._items.get_by_sku_warehouse(
            source.company_id, source.sku, to_warehouse_id
        )
        if dest is None:
            dest = InventoryItem(
                company_id=source.company_id,
                warehouse_id=to_warehouse_id,
                sku=source.sku,
                name=source.name,
                category=source.category,
                barcode=source.barcode,
                unit=source.unit,
                quantity_on_hand=0,
                min_quantity=source.min_quantity,
                purchase_price=source.purchase_price,
                sale_price=source.sale_price,
                notes=source.notes,
                is_active=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
            try:
                self._items.add(dest)
            except Exception as exc:  # noqa: BLE001
                raise ValidationError(
                    "Qisman oʻtkazma uchun maqsad omborda SKU yaratib boʻlmadi "
                    "(eski unikal cheklov). Toʻliq miqdorni oʻtkazing."
                ) from exc

        dest.quantity_on_hand += quantity
        dest.updated_by = actor_id
        self._items.save(dest)
        self._items.add_movement(
            StockMovement(
                company_id=dest.company_id,
                item_id=dest.id,
                warehouse_id=dest.warehouse_id,
                movement_type=StockMovementType.TRANSFER.value,
                quantity_delta=quantity,
                quantity_after=dest.quantity_on_hand,
                reason=reason or "Omborlararo kirim",
                reference=ref,
                moved_by=actor_id,
            )
        )
        self._audit.record(
            "inventory_transferred",
            actor_id=actor_id,
            entity_type="InventoryItem",
            entity_id=source.id,
            entity_uuid=source.uuid,
            message=f"{ref}:{quantity}",
        )
        return source

    def _clear_default_warehouse(self, company_id: int) -> None:
        for warehouse in self._warehouses.list_active(company_id):
            if warehouse.is_default:
                warehouse.is_default = False
                self._warehouses.save(warehouse)
