"""Finance main page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.customers.services.customer_service import CustomerService
from app.modules.finance.models.enums import InvoiceStatus, invoice_status_label
from app.modules.finance.models.invoice import Invoice
from app.modules.finance.schemas.finance_schema import (
    CashSessionCloseSchema,
    CashSessionOpenSchema,
)
from app.modules.finance.services.finance_service import FinanceService
from app.modules.finance.views.finance_dialogs import InvoiceFormDialog, PaymentFormDialog
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.ui.widgets.toast import show_toast


class FinancePage(QWidget):
    """Invoices, payments, and cash register controls."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._invoices: list[Invoice] = []
        self._customer_names: dict[int, str] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("finance.title"), objectName="PageTitle"))

        cash_row = QHBoxLayout()
        self._cash_label = QLabel()
        open_cash_btn = QPushButton(tr("finance.open_cash"))
        open_cash_btn.clicked.connect(self._open_cash)
        close_cash_btn = QPushButton(tr("finance.close_cash"))
        close_cash_btn.clicked.connect(self._close_cash)
        cash_row.addWidget(self._cash_label)
        cash_row.addStretch()
        cash_row.addWidget(open_cash_btn)
        cash_row.addWidget(close_cash_btn)
        root.addLayout(cash_row)

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("finance.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        self._status = QComboBox()
        self._status.addItem(tr("finance.all_statuses"), None)
        for status in InvoiceStatus:
            self._status.addItem(invoice_status_label(status), status.value)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("finance.invoice_add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_invoice)
        from_wo_btn = QPushButton(tr("finance.from_work_order"))
        from_wo_btn.clicked.connect(self._from_work_order)
        pay_btn = QPushButton(tr("finance.take_payment"))
        pay_btn.clicked.connect(self._take_payment)
        void_btn = QPushButton(tr("finance.void"))
        void_btn.setObjectName("DangerButton")
        void_btn.clicked.connect(self._void_invoice)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(self._status)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(from_wo_btn)
        toolbar.addWidget(pay_btn)
        toolbar.addWidget(void_btn)
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                tr("finance.number"),
                tr("finance.customer"),
                tr("finance.status"),
                tr("finance.total"),
                tr("finance.paid"),
                tr("finance.balance"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        query = self._search.text().strip() or None
        status = self._status.currentData()
        db = self._container.create_session()
        try:
            service = FinanceService(db)
            self._invoices = service.list_invoices(
                self._session.user.company_id,
                query=query,
                status=status,
            )
            customers = CustomerService(db).list_customers(self._session.user.company_id)
            self._customer_names = {c.id: c.display_name for c in customers}
            cash = service.get_open_cash_session(self._session.user.company_id)
            if cash is None:
                self._cash_label.setText(tr("finance.cash_closed"))
            else:
                self._cash_label.setText(
                    tr(
                        "finance.cash_open",
                        balance=f"{cash.opening_balance:,}".replace(",", " "),
                    )
                )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._invoices = []
        finally:
            db.close()
        self._fill_table()

    def _fill_table(self) -> None:
        self._table.setRowCount(0)
        for row, invoice in enumerate(self._invoices):
            self._table.insertRow(row)
            values = [
                invoice.number,
                self._customer_names.get(invoice.customer_id, str(invoice.customer_id)),
                invoice_status_label(invoice.status),
                f"{invoice.total_amount:,}".replace(",", " "),
                f"{invoice.paid_amount:,}".replace(",", " "),
                f"{invoice.balance_due:,}".replace(",", " "),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, invoice.id)
                self._table.setItem(row, col, item)

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _add_invoice(self) -> None:
        db = self._container.create_session()
        try:
            customers = [
                (c.id, f"{c.display_name} ({c.phone})")
                for c in CustomerService(db).list_customers(self._session.user.company_id)
            ]
            work_orders = [
                (w.id, w.number, w.customer_id)
                for w in WorkOrderService(db).list_work_orders(self._session.user.company_id)
            ]
        finally:
            db.close()
        if not customers:
            QMessageBox.information(self, tr("finance.title"), tr("finance.need_customer"))
            return
        dialog = InvoiceFormDialog(self, customers=customers, work_orders=work_orders)
        if dialog.exec() != InvoiceFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            FinanceService(db).create_invoice(
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

    def _from_work_order(self) -> None:
        db = self._container.create_session()
        try:
            orders = WorkOrderService(db).list_work_orders(self._session.user.company_id)
        finally:
            db.close()
        if not orders:
            QMessageBox.information(self, tr("finance.title"), tr("finance.need_work_order"))
            return
        # Use newest order with a price
        priced = [o for o in orders if (o.final_cost or o.estimated_cost or 0) > 0]
        if not priced:
            QMessageBox.information(self, tr("finance.title"), tr("finance.wo_no_price"))
            return
        work_order = priced[0]
        answer = QMessageBox.question(
            self,
            tr("finance.from_work_order"),
            tr("finance.from_wo_confirm", number=work_order.number),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            invoice = FinanceService(db).create_invoice_from_work_order(
                self._session.user.company_id,
                work_order.id,
                actor_id=self._session.user_id,
            )
            db.commit()
            show_toast(
                self,
                tr("finance.invoice_created", number=invoice.number),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _take_payment(self) -> None:
        invoice_id = self._selected_id()
        if invoice_id is None:
            QMessageBox.information(self, tr("finance.title"), tr("finance.select_first"))
            return
        invoice = next((i for i in self._invoices if i.id == invoice_id), None)
        if invoice is None or invoice.balance_due <= 0:
            QMessageBox.information(self, tr("finance.title"), tr("finance.nothing_to_pay"))
            return
        dialog = PaymentFormDialog(self, invoice_id=invoice.id, balance_due=invoice.balance_due)
        if dialog.exec() != PaymentFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            FinanceService(db).record_payment(
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

    def _void_invoice(self) -> None:
        invoice_id = self._selected_id()
        if invoice_id is None:
            QMessageBox.information(self, tr("finance.title"), tr("finance.select_first"))
            return
        answer = QMessageBox.question(self, tr("finance.void"), tr("finance.void_confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            FinanceService(db).void_invoice(invoice_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _open_cash(self) -> None:
        db = self._container.create_session()
        try:
            FinanceService(db).open_cash_session(
                self._session.user.company_id,
                CashSessionOpenSchema(opening_balance=0),
                actor_id=self._session.user_id,
            )
            db.commit()
            QMessageBox.information(self, tr("finance.title"), tr("finance.cash_opened"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _close_cash(self) -> None:
        db = self._container.create_session()
        try:
            service = FinanceService(db)
            session = service.get_open_cash_session(self._session.user.company_id)
            if session is None:
                QMessageBox.information(self, tr("finance.title"), tr("finance.cash_closed"))
                return
            service.close_cash_session(
                self._session.user.company_id,
                CashSessionCloseSchema(closing_balance=session.opening_balance),
                actor_id=self._session.user_id,
            )
            db.commit()
            QMessageBox.information(self, tr("finance.title"), tr("finance.cash_closed_ok"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
