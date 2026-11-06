"""Customer create/edit dialog."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from app.localization.translator import tr
from app.modules.customers.models.customer import Customer
from app.modules.customers.schemas.customer_schema import (
    CustomerCreateSchema,
    CustomerUpdateSchema,
)


class CustomerFormDialog(QDialog):
    """Dialog for creating or editing a customer."""

    def __init__(self, parent=None, *, customer: Customer | None = None) -> None:
        super().__init__(parent)
        self._customer = customer
        self._payload: CustomerCreateSchema | CustomerUpdateSchema | None = None
        self.setWindowTitle(
            tr("customers.edit_title") if customer else tr("customers.new_title")
        )
        self.setMinimumWidth(420)
        self._build_ui()
        if customer is not None:
            self._fill(customer)

    @property
    def payload(self) -> CustomerCreateSchema | CustomerUpdateSchema | None:
        return self._payload

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._address = QLineEdit()
        self._tax_id = QLineEdit()
        self._type = QComboBox()
        self._type.addItem(tr("customers.type_individual"), "individual")
        self._type.addItem(tr("customers.type_company"), "company")
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)

        form.addRow(tr("customers.name"), self._name)
        form.addRow(tr("customers.phone"), self._phone)
        form.addRow(tr("customers.email"), self._email)
        form.addRow(tr("customers.address"), self._address)
        form.addRow(tr("customers.type"), self._type)
        form.addRow(tr("customers.tax_id"), self._tax_id)
        form.addRow(tr("customers.notes"), self._notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, customer: Customer) -> None:
        self._name.setText(customer.display_name)
        self._phone.setText(customer.phone)
        self._email.setText(customer.email or "")
        self._address.setText(customer.address or "")
        self._tax_id.setText(customer.tax_id or "")
        self._notes.setPlainText(customer.notes or "")
        index = self._type.findData(customer.customer_type)
        if index >= 0:
            self._type.setCurrentIndex(index)

    def _on_save(self) -> None:
        data = {
            "display_name": self._name.text(),
            "phone": self._phone.text(),
            "email": self._email.text(),
            "address": self._address.text(),
            "tax_id": self._tax_id.text(),
            "customer_type": self._type.currentData(),
            "notes": self._notes.toPlainText(),
        }
        try:
            if self._customer is None:
                self._payload = CustomerCreateSchema.model_validate(data)
            else:
                self._payload = CustomerUpdateSchema.model_validate(
                    {
                        **data,
                        "is_active": self._customer.is_active,
                        "is_blacklisted": self._customer.is_blacklisted,
                    }
                )
            self.accept()
        except PydanticValidationError as exc:
            message = exc.errors()[0].get("msg", tr("common.error"))
            QMessageBox.warning(self, tr("common.error"), str(message))
