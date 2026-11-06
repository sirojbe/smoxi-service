"""Stock adjustment dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.localization.translator import tr
from app.modules.inventory.models.enums import StockMovementType
from app.modules.inventory.schemas.item_schema import StockAdjustSchema


class StockAdjustDialog(QDialog):
    """Dialog for in/out/adjust stock movements."""

    def __init__(self, parent=None, *, current_qty: int = 0) -> None:
        super().__init__(parent)
        self._current_qty = current_qty
        self._payload: StockAdjustSchema | None = None
        self.setWindowTitle(tr("inventory.adjust_title"))
        self.setMinimumWidth(400)
        self._build_ui()

    @property
    def payload(self) -> StockAdjustSchema | None:
        return self._payload

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._type = QComboBox()
        self._type.addItem(tr("inventory.move_in"), StockMovementType.IN.value)
        self._type.addItem(tr("inventory.move_out"), StockMovementType.OUT.value)
        self._type.addItem(tr("inventory.move_adjust"), StockMovementType.ADJUST.value)
        self._type.currentIndexChanged.connect(self._on_type_changed)

        self._qty = QSpinBox()
        self._qty.setRange(0, 10_000_000)
        self._qty.setValue(1)
        self._reason = QLineEdit()
        self._reference = QLineEdit()

        form.addRow(tr("inventory.movement_type"), self._type)
        form.addRow(tr("inventory.quantity"), self._qty)
        form.addRow(tr("inventory.reason"), self._reason)
        form.addRow(tr("inventory.reference"), self._reference)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._on_type_changed()

    def _on_type_changed(self) -> None:
        if self._type.currentData() == StockMovementType.ADJUST.value:
            self._qty.setValue(self._current_qty)
        elif self._qty.value() == 0:
            self._qty.setValue(1)

    def _save(self) -> None:
        self._payload = StockAdjustSchema(
            movement_type=self._type.currentData(),
            quantity=self._qty.value(),
            reason=self._reason.text(),
            reference=self._reference.text(),
        )
        self.accept()
