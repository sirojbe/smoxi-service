"""Inventory item create/edit dialog."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from app.localization.translator import tr
from app.modules.inventory.models.item import InventoryItem
from app.modules.inventory.schemas.item_schema import (
    InventoryItemCreateSchema,
    InventoryItemUpdateSchema,
)


class InventoryItemFormDialog(QDialog):
    """Dialog for creating or editing inventory items."""

    def __init__(self, parent=None, *, item: InventoryItem | None = None) -> None:
        super().__init__(parent)
        self._item = item
        self._payload: InventoryItemCreateSchema | InventoryItemUpdateSchema | None = None
        self.setWindowTitle(
            tr("inventory.edit_title") if item else tr("inventory.new_title")
        )
        self.setMinimumWidth(440)
        self._build_ui()
        if item is not None:
            self._fill(item)

    @property
    def payload(self) -> InventoryItemCreateSchema | InventoryItemUpdateSchema | None:
        return self._payload

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._sku = QLineEdit()
        self._name = QLineEdit()
        self._category = QLineEdit()
        self._barcode = QLineEdit()
        self._unit = QLineEdit()
        self._unit.setText("dona")
        self._qty = QSpinBox()
        self._qty.setRange(0, 10_000_000)
        self._min = QSpinBox()
        self._min.setRange(0, 10_000_000)
        self._purchase = QSpinBox()
        self._purchase.setRange(0, 1_000_000_000)
        self._purchase.setSuffix(" soʻm")
        self._sale = QSpinBox()
        self._sale.setRange(0, 1_000_000_000)
        self._sale.setSuffix(" soʻm")
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(70)

        form.addRow(tr("inventory.sku"), self._sku)
        form.addRow(tr("inventory.name"), self._name)
        form.addRow(tr("inventory.category"), self._category)
        form.addRow(tr("inventory.barcode"), self._barcode)
        form.addRow(tr("inventory.unit"), self._unit)
        if self._item is None:
            form.addRow(tr("inventory.quantity"), self._qty)
        form.addRow(tr("inventory.min_quantity"), self._min)
        form.addRow(tr("inventory.purchase_price"), self._purchase)
        form.addRow(tr("inventory.sale_price"), self._sale)
        form.addRow(tr("inventory.notes"), self._notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, item: InventoryItem) -> None:
        self._sku.setText(item.sku)
        self._name.setText(item.name)
        self._category.setText(item.category or "")
        self._barcode.setText(item.barcode or "")
        self._unit.setText(item.unit)
        self._qty.setValue(item.quantity_on_hand)
        self._min.setValue(item.min_quantity)
        self._purchase.setValue(item.purchase_price)
        self._sale.setValue(item.sale_price)
        self._notes.setPlainText(item.notes or "")

    def _on_save(self) -> None:
        data = {
            "sku": self._sku.text(),
            "name": self._name.text(),
            "category": self._category.text(),
            "barcode": self._barcode.text(),
            "unit": self._unit.text() or "dona",
            "quantity_on_hand": self._qty.value() if self._item is None else 0,
            "min_quantity": self._min.value(),
            "purchase_price": self._purchase.value(),
            "sale_price": self._sale.value(),
            "notes": self._notes.toPlainText(),
        }
        try:
            if self._item is None:
                self._payload = InventoryItemCreateSchema.model_validate(data)
            else:
                self._payload = InventoryItemUpdateSchema.model_validate(
                    {**data, "is_active": self._item.is_active}
                )
            self.accept()
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
