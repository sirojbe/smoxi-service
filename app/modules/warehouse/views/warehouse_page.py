"""Warehouse management page — list, CRUD, stock transfer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.inventory.models.warehouse import Warehouse
from app.modules.inventory.services.inventory_service import InventoryService


class WarehouseFormDialog(QDialog):
    def __init__(self, parent=None, *, warehouse: Warehouse | None = None) -> None:
        super().__init__(parent)
        self._warehouse = warehouse
        self.setWindowTitle(
            tr("warehouse.edit_title") if warehouse else tr("warehouse.new_title")
        )
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._code = QLineEdit()
        self._name = QLineEdit()
        self._address = QLineEdit()
        self._default = QCheckBox(tr("warehouse.is_default"))
        self._active = QCheckBox(tr("warehouse.active"))
        self._active.setChecked(True)
        form.addRow(tr("warehouse.code"), self._code)
        form.addRow(tr("warehouse.name"), self._name)
        form.addRow(tr("warehouse.address"), self._address)
        form.addRow(self._default)
        if warehouse is not None:
            form.addRow(self._active)
            self._code.setText(warehouse.code)
            self._name.setText(warehouse.name)
            self._address.setText(warehouse.address or "")
            self._default.setChecked(warehouse.is_default)
            self._active.setChecked(warehouse.is_active)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def code(self) -> str:
        return self._code.text()

    @property
    def name(self) -> str:
        return self._name.text()

    @property
    def address(self) -> str:
        return self._address.text()

    @property
    def is_default(self) -> bool:
        return self._default.isChecked()

    @property
    def is_active(self) -> bool:
        return self._active.isChecked()


class WarehousePage(QWidget):
    """Warehouse list and inter-warehouse transfer."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._warehouses: list[Warehouse] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("warehouse.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("warehouse.subtitle")))

        toolbar = QHBoxLayout()
        add_btn = QPushButton(tr("warehouse.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton(tr("warehouse.edit"))
        edit_btn.clicked.connect(self._edit)
        delete_btn = QPushButton(tr("warehouse.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete)
        transfer_btn = QPushButton(tr("warehouse.transfer"))
        transfer_btn.clicked.connect(self._transfer)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addWidget(transfer_btn)
        toolbar.addStretch()
        toolbar.addWidget(refresh_btn)
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                tr("warehouse.code"),
                tr("warehouse.name"),
                tr("warehouse.address"),
                tr("warehouse.status"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            self._warehouses = InventoryService(db).list_warehouses(
                self._session.user.company_id
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._warehouses = []
        finally:
            db.close()
        self._table.setRowCount(0)
        for row, wh in enumerate(self._warehouses):
            self._table.insertRow(row)
            status = tr("warehouse.default") if wh.is_default else tr("warehouse.ok")
            values = [wh.code, wh.name, wh.address or "", status]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, wh.id)
                self._table.setItem(row, col, item)

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _add(self) -> None:
        dialog = WarehouseFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).create_warehouse(
                self._session.user.company_id,
                code=dialog.code,
                name=dialog.name,
                address=dialog.address.strip() or None,
                is_default=dialog.is_default,
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _edit(self) -> None:
        warehouse_id = self._selected_id()
        if warehouse_id is None:
            QMessageBox.information(self, tr("warehouse.title"), tr("warehouse.select_first"))
            return
        warehouse = next((w for w in self._warehouses if w.id == warehouse_id), None)
        if warehouse is None:
            return
        dialog = WarehouseFormDialog(self, warehouse=warehouse)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).update_warehouse(
                warehouse_id,
                code=dialog.code,
                name=dialog.name,
                address=dialog.address.strip() or None,
                is_default=dialog.is_default,
                is_active=dialog.is_active,
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _delete(self) -> None:
        warehouse_id = self._selected_id()
        if warehouse_id is None:
            return
        answer = QMessageBox.question(
            self, tr("warehouse.delete"), tr("warehouse.delete_confirm")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).soft_delete_warehouse(
                warehouse_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _transfer(self) -> None:
        db = self._container.create_session()
        try:
            svc = InventoryService(db)
            items = svc.list_items(self._session.user.company_id)
            warehouses = svc.list_warehouses(self._session.user.company_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        if not items or len(warehouses) < 2:
            QMessageBox.information(
                self, tr("warehouse.title"), tr("warehouse.transfer_need")
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("warehouse.transfer"))
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        item_box = QComboBox()
        for item in items:
            label = f"{item.sku} · {item.name} ({item.quantity_on_hand})"
            item_box.addItem(label, item.id)
        dest_box = QComboBox()
        for wh in warehouses:
            dest_box.addItem(f"{wh.code} — {wh.name}", wh.id)
        qty = QSpinBox()
        qty.setRange(1, 1_000_000)
        qty.setValue(1)
        reason = QLineEdit()
        form.addRow(tr("warehouse.item"), item_box)
        form.addRow(tr("warehouse.to"), dest_box)
        form.addRow(tr("warehouse.qty"), qty)
        form.addRow(tr("warehouse.reason"), reason)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).transfer_stock(
                int(item_box.currentData()),
                to_warehouse_id=int(dest_box.currentData()),
                quantity=qty.value(),
                reason=reason.text().strip() or None,
                actor_id=self._session.user_id,
            )
            db.commit()
            QMessageBox.information(self, tr("warehouse.title"), tr("warehouse.transfer_ok"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
