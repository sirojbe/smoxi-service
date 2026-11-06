"""B2B Companies page (UIUX §9.2)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
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
from app.modules.business_clients.models.business_client import BusinessClient
from app.modules.business_clients.schemas.business_client_schema import (
    BusinessClientCreateSchema,
    BusinessClientUpdateSchema,
    ContactCreateSchema,
)
from app.modules.business_clients.services.business_client_service import BusinessClientService
from app.modules.customers.services.customer_service import CustomerService


class BusinessClientFormDialog(QDialog):
    def __init__(self, parent=None, *, client: BusinessClient | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._payload: BusinessClientCreateSchema | BusinessClientUpdateSchema | None = None
        self.setWindowTitle(
            tr("companies.edit_title") if client else tr("companies.new_title")
        )
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._tax = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._address = QLineEdit()
        self._credit = QLineEdit()
        self._credit.setText("0")
        self._hold = QCheckBox(tr("companies.credit_hold"))
        self._active = QCheckBox(tr("companies.active"))
        self._active.setChecked(True)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(70)
        form.addRow(tr("companies.name"), self._name)
        form.addRow(tr("companies.tax_id"), self._tax)
        form.addRow(tr("companies.phone"), self._phone)
        form.addRow(tr("companies.email"), self._email)
        form.addRow(tr("companies.address"), self._address)
        form.addRow(tr("companies.credit_limit"), self._credit)
        if client is not None:
            form.addRow(self._hold)
            form.addRow(self._active)
        form.addRow(tr("companies.notes"), self._notes)
        layout.addLayout(form)
        if client is not None:
            self._name.setText(client.name)
            self._tax.setText(client.tax_id or "")
            self._phone.setText(client.phone or "")
            self._email.setText(client.email or "")
            self._address.setText(client.address or "")
            self._credit.setText(str(client.credit_limit))
            self._hold.setChecked(client.credit_hold)
            self._active.setChecked(client.is_active)
            self._notes.setPlainText(client.notes or "")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> BusinessClientCreateSchema | BusinessClientUpdateSchema | None:
        return self._payload

    def _save(self) -> None:
        try:
            limit = Decimal(self._credit.text().strip() or "0")
        except InvalidOperation:
            QMessageBox.warning(self, tr("common.error"), tr("companies.credit_invalid"))
            return
        data = {
            "name": self._name.text(),
            "tax_id": self._tax.text(),
            "phone": self._phone.text(),
            "email": self._email.text(),
            "address": self._address.text(),
            "credit_limit": limit,
            "notes": self._notes.toPlainText(),
        }
        try:
            if self._client is None:
                self._payload = BusinessClientCreateSchema.model_validate(data)
            else:
                data["credit_hold"] = self._hold.isChecked()
                data["is_active"] = self._active.isChecked()
                self._payload = BusinessClientUpdateSchema.model_validate(data)
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
            return
        self.accept()


class CompaniesPage(QWidget):
    """B2B company list with contacts and linked customers."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._clients: list[BusinessClient] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("companies.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("companies.subtitle")))

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("companies.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("companies.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton(tr("companies.edit"))
        edit_btn.clicked.connect(self._edit)
        hold_btn = QPushButton(tr("companies.toggle_hold"))
        hold_btn.clicked.connect(self._toggle_hold)
        delete_btn = QPushButton(tr("companies.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(hold_btn)
        toolbar.addWidget(delete_btn)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                tr("companies.name"),
                tr("companies.tax_id"),
                tr("companies.phone"),
                tr("companies.credit_limit"),
                tr("companies.status"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self._table)

        lower = QWidget()
        lower_layout = QHBoxLayout(lower)
        contacts_box = QVBoxLayout()
        contacts_box.addWidget(QLabel(tr("companies.contacts")))
        c_row = QHBoxLayout()
        add_c = QPushButton(tr("companies.add_contact"))
        add_c.clicked.connect(self._add_contact)
        del_c = QPushButton(tr("companies.delete_contact"))
        del_c.clicked.connect(self._delete_contact)
        c_row.addWidget(add_c)
        c_row.addWidget(del_c)
        c_row.addStretch()
        contacts_box.addLayout(c_row)
        self._contacts = QTableWidget(0, 3)
        self._contacts.setHorizontalHeaderLabels(
            [tr("companies.contact_name"), tr("companies.phone"), tr("companies.job_title")]
        )
        self._contacts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._contacts.horizontalHeader().setStretchLastSection(True)
        contacts_box.addWidget(self._contacts)
        lower_layout.addLayout(contacts_box)

        linked_box = QVBoxLayout()
        linked_box.addWidget(QLabel(tr("companies.linked_customers")))
        l_row = QHBoxLayout()
        link_btn = QPushButton(tr("companies.link_customer"))
        link_btn.clicked.connect(self._link_customer)
        unlink_btn = QPushButton(tr("companies.unlink_customer"))
        unlink_btn.clicked.connect(self._unlink_customer)
        l_row.addWidget(link_btn)
        l_row.addWidget(unlink_btn)
        l_row.addStretch()
        linked_box.addLayout(l_row)
        self._linked = QTableWidget(0, 2)
        self._linked.setHorizontalHeaderLabels(
            [tr("customers.name"), tr("customers.phone")]
        )
        self._linked.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._linked.horizontalHeader().setStretchLastSection(True)
        linked_box.addWidget(self._linked)
        lower_layout.addLayout(linked_box)
        splitter.addWidget(lower)
        splitter.setSizes([360, 240])
        root.addWidget(splitter, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            self._clients = BusinessClientService(db).list_clients(
                self._session.user.company_id,
                query=self._search.text().strip() or None,
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._clients = []
        finally:
            db.close()
        self._table.setRowCount(0)
        for row, client in enumerate(self._clients):
            self._table.insertRow(row)
            status = tr("companies.hold") if client.credit_hold else tr("companies.ok")
            if not client.is_active:
                status = tr("companies.inactive")
            values = [
                client.name,
                client.tax_id or "",
                client.phone or "",
                str(client.credit_limit),
                status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, client.id)
                self._table.setItem(row, col, item)
        self._on_select()

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _on_select(self) -> None:
        client_id = self._selected_id()
        self._contacts.setRowCount(0)
        self._linked.setRowCount(0)
        if client_id is None:
            return
        db = self._container.create_session()
        try:
            svc = BusinessClientService(db)
            client = svc.get_client(client_id)
            contacts = [c for c in client.contacts if c.deleted_at is None]
            for row, contact in enumerate(contacts):
                self._contacts.insertRow(row)
                for col, value in enumerate(
                    [contact.full_name, contact.phone or "", contact.job_title or ""]
                ):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.ItemDataRole.UserRole, contact.id)
                    self._contacts.setItem(row, col, item)
            for row, customer in enumerate(svc.list_linked_customers(client_id)):
                self._linked.insertRow(row)
                for col, value in enumerate([customer.display_name, customer.phone]):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.ItemDataRole.UserRole, customer.id)
                    self._linked.setItem(row, col, item)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _add(self) -> None:
        dialog = BusinessClientFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            BusinessClientService(db).create_client(
                self._session.user.company_id,
                dialog.payload,  # type: ignore[arg-type]
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
        client_id = self._selected_id()
        if client_id is None:
            QMessageBox.information(self, tr("companies.title"), tr("companies.select_first"))
            return
        db = self._container.create_session()
        try:
            client = BusinessClientService(db).get_client(client_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        dialog = BusinessClientFormDialog(self, client=client)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            BusinessClientService(db).update_client(
                client_id,
                dialog.payload,  # type: ignore[arg-type]
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

    def _toggle_hold(self) -> None:
        client_id = self._selected_id()
        if client_id is None:
            return
        db = self._container.create_session()
        try:
            svc = BusinessClientService(db)
            client = svc.get_client(client_id)
            svc.set_credit_hold(
                client_id, not client.credit_hold, actor_id=self._session.user_id
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
        client_id = self._selected_id()
        if client_id is None:
            return
        answer = QMessageBox.question(
            self, tr("companies.delete"), tr("companies.delete_confirm")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            BusinessClientService(db).soft_delete_client(
                client_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _add_contact(self) -> None:
        client_id = self._selected_id()
        if client_id is None:
            return
        name, ok = QInputDialog.getText(self, tr("companies.add_contact"), tr("companies.contact_name"))
        if not ok or not name.strip():
            return
        phone, _ = QInputDialog.getText(self, tr("companies.add_contact"), tr("companies.phone"))
        try:
            payload = ContactCreateSchema(full_name=name, phone=phone or None)
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
            return
        db = self._container.create_session()
        try:
            BusinessClientService(db).add_contact(
                client_id, payload, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._on_select()

    def _delete_contact(self) -> None:
        rows = self._contacts.selectionModel().selectedRows()
        if not rows:
            return
        item = self._contacts.item(rows[0].row(), 0)
        if item is None:
            return
        contact_id = int(item.data(Qt.ItemDataRole.UserRole))
        db = self._container.create_session()
        try:
            BusinessClientService(db).delete_contact(
                contact_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._on_select()

    def _link_customer(self) -> None:
        client_id = self._selected_id()
        if client_id is None:
            return
        db = self._container.create_session()
        try:
            customers = CustomerService(db).list_customers(self._session.user.company_id)
            options = [
                (c.display_name, c.id)
                for c in customers
                if c.business_client_id is None
            ]
        finally:
            db.close()
        if not options:
            QMessageBox.information(self, tr("companies.title"), tr("companies.no_customers"))
            return
        labels = [o[0] for o in options]
        choice, ok = QInputDialog.getItem(
            self, tr("companies.link_customer"), tr("customers.name"), labels, 0, False
        )
        if not ok:
            return
        customer_id = options[labels.index(choice)][1]
        db = self._container.create_session()
        try:
            BusinessClientService(db).link_customer(
                client_id, customer_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._on_select()

    def _unlink_customer(self) -> None:
        rows = self._linked.selectionModel().selectedRows()
        if not rows:
            return
        item = self._linked.item(rows[0].row(), 0)
        if item is None:
            return
        customer_id = int(item.data(Qt.ItemDataRole.UserRole))
        db = self._container.create_session()
        try:
            BusinessClientService(db).unlink_customer(
                customer_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._on_select()
