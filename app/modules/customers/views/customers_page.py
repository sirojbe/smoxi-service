"""Customers list page with Customer 360 detail tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.customers.models.customer import Customer
from app.modules.customers.models.device import Device
from app.modules.customers.schemas.customer_schema import (
    CustomerCreateSchema,
    CustomerUpdateSchema,
    DeviceCreateSchema,
    DeviceUpdateSchema,
)
from app.modules.customers.services.customer_service import CustomerService
from app.modules.customers.views.customer_form_dialog import CustomerFormDialog
from app.modules.customers.views.device_form_dialog import DeviceFormDialog
from app.modules.finance.models.enums import invoice_status_label
from app.modules.finance.models.invoice import Invoice, Payment
from app.modules.finance.services.finance_service import FinanceService
from app.modules.work_orders.models.status import status_label
from app.modules.work_orders.models.work_order import WorkOrder
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository


class CustomersPage(QWidget):
    """Customer list with 360° overview, devices, WOs, invoices, payments."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._customers: list[Customer] = []
        self._devices: list[Device] = []
        self._work_orders: list[WorkOrder] = []
        self._invoices: list[Invoice] = []
        self._payments: list[Payment] = []
        self._selected_customer: Customer | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel(tr("customers.title"), objectName="PageTitle")
        root.addWidget(title)

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("customers.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("customers.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_customer)
        edit_btn = QPushButton(tr("customers.edit"))
        edit_btn.clicked.connect(self._edit_customer)
        delete_btn = QPushButton(tr("customers.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_customer)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(delete_btn)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                tr("customers.name"),
                tr("customers.phone"),
                tr("customers.email"),
                tr("customers.devices_count"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_customer_selected)
        splitter.addWidget(self._table)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_overview_tab(), tr("customers.tab_overview"))
        self._tabs.addTab(self._build_devices_tab(), tr("customers.tab_devices"))
        self._tabs.addTab(self._build_work_orders_tab(), tr("customers.tab_work_orders"))
        self._tabs.addTab(self._build_invoices_tab(), tr("customers.tab_invoices"))
        self._tabs.addTab(self._build_payments_tab(), tr("customers.tab_payments"))
        splitter.addWidget(self._tabs)
        splitter.setSizes([400, 280])
        root.addWidget(splitter, stretch=1)

    def _build_overview_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        self._overview_empty = QLabel(tr("customers.overview_empty"))
        self._overview_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overview_empty.setObjectName("HintLabel")
        layout.addWidget(self._overview_empty)
        form = QFormLayout()
        self._ov_name = QLabel("—")
        self._ov_phone = QLabel("—")
        self._ov_email = QLabel("—")
        self._ov_address = QLabel("—")
        self._ov_notes = QLabel("—")
        self._ov_notes.setWordWrap(True)
        form.addRow(tr("customers.name"), self._ov_name)
        form.addRow(tr("customers.phone"), self._ov_phone)
        form.addRow(tr("customers.email"), self._ov_email)
        form.addRow(tr("customers.address"), self._ov_address)
        form.addRow(tr("customers.notes"), self._ov_notes)
        self._overview_form = QWidget()
        self._overview_form.setLayout(form)
        layout.addWidget(self._overview_form)
        layout.addStretch()
        return panel

    def _build_devices_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        header.addStretch()
        add_device_btn = QPushButton(tr("customers.device_add"))
        add_device_btn.clicked.connect(self._add_device)
        edit_device_btn = QPushButton(tr("customers.edit"))
        edit_device_btn.clicked.connect(self._edit_device)
        delete_device_btn = QPushButton(tr("customers.delete"))
        delete_device_btn.clicked.connect(self._delete_device)
        header.addWidget(add_device_btn)
        header.addWidget(edit_device_btn)
        header.addWidget(delete_device_btn)
        layout.addLayout(header)

        self._devices_table = QTableWidget(0, 4)
        self._devices_table.setHorizontalHeaderLabels(
            [
                tr("customers.device_type"),
                tr("customers.model"),
                tr("customers.imei"),
                tr("customers.serial"),
            ]
        )
        self._devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._devices_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._devices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._devices_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._devices_table)
        return panel

    def _build_work_orders_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        self._wo_table = QTableWidget(0, 3)
        self._wo_table.setHorizontalHeaderLabels(
            [
                tr("work_orders.number"),
                tr("work_orders.status"),
                tr("customers.created"),
            ]
        )
        self._wo_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._wo_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._wo_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._wo_table)
        self._wo_empty = QLabel(tr("customers.wo_empty"))
        self._wo_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wo_empty.setObjectName("HintLabel")
        layout.addWidget(self._wo_empty)
        return panel

    def _build_invoices_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        self._inv_table = QTableWidget(0, 4)
        self._inv_table.setHorizontalHeaderLabels(
            [
                tr("finance.number"),
                tr("finance.status"),
                tr("finance.total"),
                tr("finance.balance"),
            ]
        )
        self._inv_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._inv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._inv_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._inv_table)
        self._inv_empty = QLabel(tr("customers.invoice_empty"))
        self._inv_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inv_empty.setObjectName("HintLabel")
        layout.addWidget(self._inv_empty)
        return panel

    def _build_payments_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        self._pay_table = QTableWidget(0, 4)
        self._pay_table.setHorizontalHeaderLabels(
            [
                tr("payments.paid_at"),
                tr("payments.invoice"),
                tr("payments.amount"),
                tr("payments.method"),
            ]
        )
        self._pay_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pay_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pay_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._pay_table)
        self._pay_empty = QLabel(tr("customers.payment_empty"))
        self._pay_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pay_empty.setObjectName("HintLabel")
        layout.addWidget(self._pay_empty)
        return panel

    def refresh(self) -> None:
        """Reload customers from the database."""
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            service = CustomerService(db)
            self._customers = service.list_customers(
                self._session.user.company_id,
                query=query,
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._customers = []
        finally:
            db.close()
        self._fill_customers()
        self._clear_detail()

    def focus_entity(self, entity_id: object) -> None:
        """Select a customer by id (Global Search)."""
        try:
            customer_id = int(entity_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        self._search.clear()
        self.refresh()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and int(item.data(Qt.ItemDataRole.UserRole)) == customer_id:
                self._table.selectRow(row)
                self._table.scrollToItem(item)
                return

    def _fill_customers(self) -> None:
        self._table.setRowCount(0)
        for row, customer in enumerate(self._customers):
            self._table.insertRow(row)
            active_devices = [d for d in customer.devices if d.deleted_at is None]
            values = [
                customer.display_name,
                customer.phone,
                customer.email or "",
                str(len(active_devices)),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, customer.id)
                self._table.setItem(row, col, item)

    def _selected_customer_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _selected_device_id(self) -> int | None:
        rows = self._devices_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._devices_table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _clear_detail(self) -> None:
        self._selected_customer = None
        self._devices = []
        self._work_orders = []
        self._invoices = []
        self._payments = []
        self._fill_overview()
        self._fill_devices()
        self._fill_work_orders()
        self._fill_invoices()
        self._fill_payments()

    def _on_customer_selected(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is None:
            self._clear_detail()
            return
        db = self._container.create_session()
        try:
            customer = CustomerService(db).get_customer(customer_id)
            self._selected_customer = customer
            self._devices = [d for d in customer.devices if d.deleted_at is None]
            finance = FinanceService(db)
            self._work_orders = WorkOrderRepository(db).list_for_customer(customer_id, limit=50)
            self._invoices = finance.list_invoices_for_customer(customer_id, limit=50)
            self._payments = finance.list_payments_for_customer(customer_id, limit=50)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._clear_detail()
            return
        finally:
            db.close()
        self._fill_overview()
        self._fill_devices()
        self._fill_work_orders()
        self._fill_invoices()
        self._fill_payments()

    def _fill_overview(self) -> None:
        customer = self._selected_customer
        empty = customer is None
        self._overview_empty.setVisible(empty)
        self._overview_form.setVisible(not empty)
        if customer is None:
            self._ov_name.setText("—")
            self._ov_phone.setText("—")
            self._ov_email.setText("—")
            self._ov_address.setText("—")
            self._ov_notes.setText("—")
            return
        self._ov_name.setText(customer.display_name)
        self._ov_phone.setText(customer.phone)
        self._ov_email.setText(customer.email or "—")
        self._ov_address.setText(customer.address or "—")
        self._ov_notes.setText(customer.notes or "—")

    def _fill_devices(self) -> None:
        self._devices_table.setRowCount(0)
        for row, device in enumerate(self._devices):
            self._devices_table.insertRow(row)
            values = [
                device.device_type,
                device.display_label,
                device.imei or "",
                device.serial_number or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, device.id)
                self._devices_table.setItem(row, col, item)

    def _fill_work_orders(self) -> None:
        self._wo_table.setRowCount(0)
        for order in self._work_orders:
            row = self._wo_table.rowCount()
            self._wo_table.insertRow(row)
            created = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else ""
            values = [order.number, status_label(order.status), created]
            for col, value in enumerate(values):
                self._wo_table.setItem(row, col, QTableWidgetItem(value))
        empty = len(self._work_orders) == 0
        self._wo_empty.setVisible(empty)
        self._wo_table.setVisible(not empty)

    def _fill_invoices(self) -> None:
        self._inv_table.setRowCount(0)
        for invoice in self._invoices:
            row = self._inv_table.rowCount()
            self._inv_table.insertRow(row)
            values = [
                invoice.number,
                invoice_status_label(invoice.status),
                f"{invoice.total_amount:,}".replace(",", " "),
                f"{invoice.balance_due:,}".replace(",", " "),
            ]
            for col, value in enumerate(values):
                self._inv_table.setItem(row, col, QTableWidgetItem(value))
        empty = len(self._invoices) == 0
        self._inv_empty.setVisible(empty)
        self._inv_table.setVisible(not empty)

    def _fill_payments(self) -> None:
        self._pay_table.setRowCount(0)
        for payment in self._payments:
            row = self._pay_table.rowCount()
            self._pay_table.insertRow(row)
            invoice_number = ""
            if payment.invoice is not None:
                invoice_number = payment.invoice.number
            paid = payment.paid_at.strftime("%Y-%m-%d %H:%M") if payment.paid_at else ""
            values = [
                paid,
                invoice_number,
                f"{payment.amount:,}".replace(",", " "),
                payment.method,
            ]
            for col, value in enumerate(values):
                self._pay_table.setItem(row, col, QTableWidgetItem(value))
        empty = len(self._payments) == 0
        self._pay_empty.setVisible(empty)
        self._pay_table.setVisible(not empty)

    def _add_customer(self) -> None:
        dialog = CustomerFormDialog(self)
        if dialog.exec() != CustomerFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, CustomerCreateSchema)
        db = self._container.create_session()
        try:
            CustomerService(db).create_customer(
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

    def _edit_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is None:
            QMessageBox.information(self, tr("customers.title"), tr("customers.select_first"))
            return
        db = self._container.create_session()
        try:
            customer = CustomerService(db).get_customer(customer_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        dialog = CustomerFormDialog(self, customer=customer)
        if dialog.exec() != CustomerFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, CustomerUpdateSchema)
        db = self._container.create_session()
        try:
            CustomerService(db).update_customer(
                customer_id,
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

    def _delete_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is None:
            QMessageBox.information(self, tr("customers.title"), tr("customers.select_first"))
            return
        answer = QMessageBox.question(self, tr("customers.delete"), tr("customers.delete_confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            CustomerService(db).delete_customer(customer_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _add_device(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is None:
            QMessageBox.information(self, tr("customers.title"), tr("customers.select_first"))
            return
        dialog = DeviceFormDialog(self)
        if dialog.exec() != DeviceFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, DeviceCreateSchema)
        db = self._container.create_session()
        try:
            CustomerService(db).create_device(
                customer_id,
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
        self._on_customer_selected()
        self.refresh()

    def _edit_device(self) -> None:
        device_id = self._selected_device_id()
        if device_id is None:
            QMessageBox.information(self, tr("customers.devices"), tr("customers.select_device"))
            return
        device = next((d for d in self._devices if d.id == device_id), None)
        if device is None:
            return
        dialog = DeviceFormDialog(self, device=device)
        if dialog.exec() != DeviceFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, DeviceUpdateSchema)
        db = self._container.create_session()
        try:
            CustomerService(db).update_device(
                device_id,
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
        self._on_customer_selected()

    def _delete_device(self) -> None:
        device_id = self._selected_device_id()
        if device_id is None:
            QMessageBox.information(self, tr("customers.devices"), tr("customers.select_device"))
            return
        answer = QMessageBox.question(self, tr("customers.delete"), tr("customers.delete_device_confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            CustomerService(db).delete_device(device_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._on_customer_selected()
        self.refresh()
