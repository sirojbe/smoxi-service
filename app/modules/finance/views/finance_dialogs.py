"""Finance UI dialogs."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.localization.translator import tr
from app.modules.finance.models.enums import PaymentMethod, payment_method_label
from app.modules.finance.schemas.finance_schema import (
    InvoiceCreateSchema,
    InvoiceLineSchema,
    PaymentCreateSchema,
)


class InvoiceFormDialog(QDialog):
    """Create invoice with one or more lines."""

    def __init__(
        self,
        parent=None,
        *,
        customers: list[tuple[int, str]],
        work_orders: list[tuple[int, str, int]],
    ) -> None:
        super().__init__(parent)
        self._customers = customers
        self._work_orders = work_orders
        self._lines: list[InvoiceLineSchema] = []
        self._payload: InvoiceCreateSchema | None = None
        self.setWindowTitle(tr("finance.invoice_new"))
        self.setMinimumWidth(520)
        self._build_ui()

    @property
    def payload(self) -> InvoiceCreateSchema | None:
        return self._payload

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._customer = QComboBox()
        for customer_id, label in self._customers:
            self._customer.addItem(label, customer_id)
        self._work_order = QComboBox()
        self._work_order.addItem(tr("finance.no_work_order"), None)
        for wo_id, label, customer_id in self._work_orders:
            self._work_order.addItem(label, (wo_id, customer_id))
        self._discount = QSpinBox()
        self._discount.setRange(0, 1_000_000_000)
        self._discount.setSuffix(" soʻm")
        self._tax = QSpinBox()
        self._tax.setRange(0, 1_000_000_000)
        self._tax.setSuffix(" soʻm")
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(60)
        form.addRow(tr("finance.customer"), self._customer)
        form.addRow(tr("finance.work_order"), self._work_order)
        form.addRow(tr("finance.discount"), self._discount)
        form.addRow(tr("finance.tax"), self._tax)
        form.addRow(tr("finance.notes"), self._notes)
        layout.addLayout(form)

        layout.addWidget(QLabel(tr("finance.lines")))
        line_row = QHBoxLayout()
        self._line_desc = QLineEdit()
        self._line_qty = QSpinBox()
        self._line_qty.setRange(1, 100000)
        self._line_qty.setValue(1)
        self._line_price = QSpinBox()
        self._line_price.setRange(0, 1_000_000_000)
        self._line_price.setSuffix(" soʻm")
        add_line_btn = QPushButton(tr("finance.add_line"))
        add_line_btn.clicked.connect(self._add_line)
        line_row.addWidget(self._line_desc, stretch=2)
        line_row.addWidget(self._line_qty)
        line_row.addWidget(self._line_price)
        line_row.addWidget(add_line_btn)
        layout.addLayout(line_row)

        self._lines_table = QTableWidget(0, 3)
        self._lines_table.setHorizontalHeaderLabels(
            [tr("finance.description"), tr("finance.qty"), tr("finance.price")]
        )
        self._lines_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._lines_table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_line(self) -> None:
        try:
            line = InvoiceLineSchema(
                description=self._line_desc.text(),
                quantity=self._line_qty.value(),
                unit_price=self._line_price.value(),
            )
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
            return
        self._lines.append(line)
        row = self._lines_table.rowCount()
        self._lines_table.insertRow(row)
        self._lines_table.setItem(row, 0, QTableWidgetItem(line.description))
        self._lines_table.setItem(row, 1, QTableWidgetItem(str(line.quantity)))
        self._lines_table.setItem(row, 2, QTableWidgetItem(str(line.unit_price)))
        self._line_desc.clear()
        self._line_qty.setValue(1)
        self._line_price.setValue(0)

    def _save(self) -> None:
        if not self._lines:
            QMessageBox.warning(self, tr("common.error"), tr("finance.need_lines"))
            return
        wo_data = self._work_order.currentData()
        work_order_id = wo_data[0] if wo_data else None
        customer_id = self._customer.currentData()
        if wo_data and wo_data[1] != customer_id:
            QMessageBox.warning(self, tr("common.error"), tr("finance.wo_customer_mismatch"))
            return
        try:
            self._payload = InvoiceCreateSchema(
                customer_id=int(customer_id),
                work_order_id=work_order_id,
                lines=self._lines,
                discount_amount=self._discount.value(),
                tax_amount=self._tax.value(),
                notes=self._notes.toPlainText(),
                issue_immediately=True,
            )
            self.accept()
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))


class PaymentFormDialog(QDialog):
    """Take payment against an invoice."""

    def __init__(self, parent=None, *, invoice_id: int, balance_due: int) -> None:
        super().__init__(parent)
        self._invoice_id = invoice_id
        self._payload: PaymentCreateSchema | None = None
        self.setWindowTitle(tr("finance.payment_title"))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow(tr("finance.balance_due"), QLabel(f"{balance_due:,} soʻm".replace(",", " ")))
        self._amount = QSpinBox()
        self._amount.setRange(1, balance_due)
        self._amount.setValue(balance_due)
        self._amount.setSuffix(" soʻm")
        self._method = QComboBox()
        for method in PaymentMethod:
            self._method.addItem(payment_method_label(method), method.value)
        self._reference = QLineEdit()
        self._notes = QLineEdit()
        form.addRow(tr("finance.amount"), self._amount)
        form.addRow(tr("finance.method"), self._method)
        form.addRow(tr("finance.reference"), self._reference)
        form.addRow(tr("finance.notes"), self._notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> PaymentCreateSchema | None:
        return self._payload

    def _save(self) -> None:
        self._payload = PaymentCreateSchema(
            invoice_id=self._invoice_id,
            amount=self._amount.value(),
            method=self._method.currentData(),
            reference=self._reference.text(),
            notes=self._notes.text(),
        )
        self.accept()
