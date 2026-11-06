"""Suppliers and purchase orders UI."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.suppliers.models.enums import po_status_label
from app.modules.suppliers.models.supplier import PurchaseOrder, Supplier
from app.modules.suppliers.schemas.supplier_schema import (
    PurchaseOrderCreateSchema,
    PurchaseOrderLineSchema,
    SupplierCreateSchema,
    SupplierUpdateSchema,
)
from app.modules.suppliers.services.supplier_service import SupplierService


class SupplierFormDialog(QDialog):
    """Create/edit supplier."""

    def __init__(self, parent=None, *, supplier: Supplier | None = None) -> None:
        super().__init__(parent)
        self._supplier = supplier
        self._payload: SupplierCreateSchema | SupplierUpdateSchema | None = None
        self.setWindowTitle(
            tr("suppliers.edit_title") if supplier else tr("suppliers.new_title")
        )
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._code = QLineEdit()
        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._address = QLineEdit()
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(70)
        form.addRow(tr("suppliers.code"), self._code)
        form.addRow(tr("suppliers.name"), self._name)
        form.addRow(tr("suppliers.phone"), self._phone)
        form.addRow(tr("suppliers.email"), self._email)
        form.addRow(tr("suppliers.address"), self._address)
        form.addRow(tr("suppliers.notes"), self._notes)
        layout.addLayout(form)
        if supplier is not None:
            self._code.setText(supplier.code)
            self._name.setText(supplier.name)
            self._phone.setText(supplier.phone or "")
            self._email.setText(supplier.email or "")
            self._address.setText(supplier.address or "")
            self._notes.setPlainText(supplier.notes or "")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> SupplierCreateSchema | SupplierUpdateSchema | None:
        return self._payload

    def _save(self) -> None:
        data = {
            "code": self._code.text(),
            "name": self._name.text(),
            "phone": self._phone.text(),
            "email": self._email.text(),
            "address": self._address.text(),
            "notes": self._notes.toPlainText(),
        }
        try:
            if self._supplier is None:
                self._payload = SupplierCreateSchema.model_validate(data)
            else:
                self._payload = SupplierUpdateSchema.model_validate(
                    {**data, "is_active": self._supplier.is_active}
                )
            self.accept()
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))


class PurchaseOrderFormDialog(QDialog):
    """Create purchase order with inventory lines."""

    def __init__(
        self,
        parent=None,
        *,
        suppliers: list[tuple[int, str]],
        items: list[tuple[int, str]],
    ) -> None:
        super().__init__(parent)
        self._lines: list[PurchaseOrderLineSchema] = []
        self._payload: PurchaseOrderCreateSchema | None = None
        self.setWindowTitle(tr("suppliers.po_new"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._supplier = QComboBox()
        for sid, label in suppliers:
            self._supplier.addItem(label, sid)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(60)
        form.addRow(tr("suppliers.supplier"), self._supplier)
        form.addRow(tr("suppliers.notes"), self._notes)
        layout.addLayout(form)

        line_row = QHBoxLayout()
        self._item = QComboBox()
        for iid, label in items:
            self._item.addItem(label, iid)
        self._qty = QSpinBox()
        self._qty.setRange(1, 1_000_000)
        self._qty.setValue(1)
        self._cost = QSpinBox()
        self._cost.setRange(0, 1_000_000_000)
        self._cost.setSuffix(" soʻm")
        add_btn = QPushButton(tr("suppliers.add_line"))
        add_btn.clicked.connect(self._add_line)
        line_row.addWidget(self._item, stretch=2)
        line_row.addWidget(self._qty)
        line_row.addWidget(self._cost)
        line_row.addWidget(add_btn)
        layout.addLayout(line_row)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            [tr("suppliers.item"), tr("suppliers.qty"), tr("suppliers.cost")]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> PurchaseOrderCreateSchema | None:
        return self._payload

    def _add_line(self) -> None:
        item_id = self._item.currentData()
        if item_id is None:
            QMessageBox.warning(self, tr("common.error"), tr("suppliers.need_item"))
            return
        line = PurchaseOrderLineSchema(
            inventory_item_id=int(item_id),
            quantity=self._qty.value(),
            unit_cost=self._cost.value(),
        )
        self._lines.append(line)
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(self._item.currentText()))
        self._table.setItem(row, 1, QTableWidgetItem(str(line.quantity)))
        self._table.setItem(row, 2, QTableWidgetItem(str(line.unit_cost)))

    def _save(self) -> None:
        if not self._lines:
            QMessageBox.warning(self, tr("common.error"), tr("suppliers.need_lines"))
            return
        try:
            self._payload = PurchaseOrderCreateSchema(
                supplier_id=int(self._supplier.currentData()),
                lines=self._lines,
                notes=self._notes.toPlainText(),
                submit=True,
            )
            self.accept()
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))


class SuppliersPage(QWidget):
    """Suppliers list and purchase orders panel."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._suppliers: list[Supplier] = []
        self._orders: list[PurchaseOrder] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("suppliers.title"), objectName="PageTitle"))

        splitter = QSplitter(Qt.Orientation.Vertical)

        suppliers_box = QWidget()
        s_layout = QVBoxLayout(suppliers_box)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("suppliers.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("suppliers.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_supplier)
        edit_btn = QPushButton(tr("suppliers.edit"))
        edit_btn.clicked.connect(self._edit_supplier)
        delete_btn = QPushButton(tr("suppliers.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_supplier)
        s_toolbar.addWidget(self._search, stretch=1)
        s_toolbar.addWidget(search_btn)
        s_toolbar.addWidget(add_btn)
        s_toolbar.addWidget(edit_btn)
        s_toolbar.addWidget(delete_btn)
        s_layout.addLayout(s_toolbar)
        self._suppliers_table = QTableWidget(0, 4)
        self._suppliers_table.setHorizontalHeaderLabels(
            [
                tr("suppliers.code"),
                tr("suppliers.name"),
                tr("suppliers.phone"),
                tr("suppliers.email"),
            ]
        )
        self._suppliers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._suppliers_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._suppliers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._suppliers_table.horizontalHeader().setStretchLastSection(True)
        s_layout.addWidget(self._suppliers_table)
        splitter.addWidget(suppliers_box)

        po_box = QWidget()
        p_layout = QVBoxLayout(po_box)
        p_layout.setContentsMargins(0, 8, 0, 0)
        p_toolbar = QHBoxLayout()
        p_toolbar.addWidget(QLabel(tr("suppliers.purchase_orders")))
        p_toolbar.addStretch()
        new_po_btn = QPushButton(tr("suppliers.po_add"))
        new_po_btn.clicked.connect(self._add_po)
        receive_btn = QPushButton(tr("suppliers.po_receive"))
        receive_btn.setObjectName("PrimaryButton")
        receive_btn.clicked.connect(self._receive_po)
        cancel_btn = QPushButton(tr("suppliers.po_cancel"))
        cancel_btn.clicked.connect(self._cancel_po)
        p_toolbar.addWidget(new_po_btn)
        p_toolbar.addWidget(receive_btn)
        p_toolbar.addWidget(cancel_btn)
        p_layout.addLayout(p_toolbar)
        self._po_table = QTableWidget(0, 4)
        self._po_table.setHorizontalHeaderLabels(
            [
                tr("suppliers.po_number"),
                tr("suppliers.supplier"),
                tr("suppliers.status"),
                tr("suppliers.total"),
            ]
        )
        self._po_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._po_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._po_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._po_table.horizontalHeader().setStretchLastSection(True)
        p_layout.addWidget(self._po_table)
        splitter.addWidget(po_box)
        splitter.setSizes([280, 280])
        root.addWidget(splitter)
        self.refresh()

    def refresh(self) -> None:
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            service = SupplierService(db)
            self._suppliers = service.list_suppliers(
                self._session.user.company_id,
                query=query,
            )
            self._orders = service.list_purchase_orders(self._session.user.company_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._suppliers = []
            self._orders = []
        finally:
            db.close()
        self._fill_suppliers()
        self._fill_orders()

    def _fill_suppliers(self) -> None:
        self._suppliers_table.setRowCount(0)
        for row, supplier in enumerate(self._suppliers):
            self._suppliers_table.insertRow(row)
            values = [supplier.code, supplier.name, supplier.phone or "", supplier.email or ""]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, supplier.id)
                self._suppliers_table.setItem(row, col, item)

    def _fill_orders(self) -> None:
        self._po_table.setRowCount(0)
        supplier_names = {s.id: s.name for s in self._suppliers}
        for row, order in enumerate(self._orders):
            self._po_table.insertRow(row)
            name = (
                order.supplier.name
                if order.supplier is not None
                else supplier_names.get(order.supplier_id, str(order.supplier_id))
            )
            values = [
                order.number,
                name,
                po_status_label(order.status),
                f"{order.total_amount:,}".replace(",", " "),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, order.id)
                self._po_table.setItem(row, col, item)

    def _selected_supplier_id(self) -> int | None:
        rows = self._suppliers_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._suppliers_table.item(rows[0].row(), 0)
        return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))

    def _selected_po_id(self) -> int | None:
        rows = self._po_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._po_table.item(rows[0].row(), 0)
        return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))

    def _add_supplier(self) -> None:
        dialog = SupplierFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, SupplierCreateSchema)
        db = self._container.create_session()
        try:
            SupplierService(db).create_supplier(
                self._session.user.company_id,
                dialog.payload,
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

    def _edit_supplier(self) -> None:
        supplier_id = self._selected_supplier_id()
        if supplier_id is None:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.select_first"))
            return
        supplier = next((s for s in self._suppliers if s.id == supplier_id), None)
        if supplier is None:
            return
        dialog = SupplierFormDialog(self, supplier=supplier)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, SupplierUpdateSchema)
        db = self._container.create_session()
        try:
            SupplierService(db).update_supplier(
                supplier_id,
                dialog.payload,
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

    def _delete_supplier(self) -> None:
        supplier_id = self._selected_supplier_id()
        if supplier_id is None:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.select_first"))
            return
        if (
            QMessageBox.question(self, tr("suppliers.delete"), tr("suppliers.delete_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        db = self._container.create_session()
        try:
            SupplierService(db).delete_supplier(supplier_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _add_po(self) -> None:
        db = self._container.create_session()
        try:
            suppliers = [
                (s.id, f"{s.name} ({s.code})")
                for s in SupplierService(db).list_suppliers(self._session.user.company_id)
                if s.is_active
            ]
            items = [
                (i.id, f"{i.sku} — {i.name}")
                for i in InventoryService(db).list_items(self._session.user.company_id)
                if i.is_active
            ]
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        if not suppliers:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.need_supplier"))
            return
        if not items:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.need_item"))
            return
        dialog = PurchaseOrderFormDialog(self, suppliers=suppliers, items=items)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            order = SupplierService(db).create_purchase_order(
                self._session.user.company_id,
                dialog.payload,
                actor_id=self._session.user_id,
            )
            db.commit()
            QMessageBox.information(
                self,
                tr("suppliers.title"),
                tr("suppliers.po_created", number=order.number),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _receive_po(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.select_po"))
            return
        if (
            QMessageBox.question(self, tr("suppliers.po_receive"), tr("suppliers.po_receive_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        db = self._container.create_session()
        try:
            SupplierService(db).receive_purchase_order(po_id, actor_id=self._session.user_id)
            db.commit()
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.po_received"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _cancel_po(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            QMessageBox.information(self, tr("suppliers.title"), tr("suppliers.select_po"))
            return
        if (
            QMessageBox.question(self, tr("suppliers.po_cancel"), tr("suppliers.po_cancel_confirm"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        db = self._container.create_session()
        try:
            SupplierService(db).cancel_purchase_order(po_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
