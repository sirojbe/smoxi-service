"""Payments (cashier) list page — blueprint §9.11."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
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
from app.modules.finance.models.invoice import Payment
from app.modules.finance.services.finance_service import FinanceService
from app.modules.finance.views.finance_dialogs import PaymentFormDialog
from app.ui.widgets.toast import show_toast


class PaymentsPage(QWidget):
    """Standalone payment list and take-payment cashier surface."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._payments: list[Payment] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        root.addWidget(QLabel(tr("payments.title"), objectName="PageTitle"))

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("payments.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        take_btn = QPushButton(tr("payments.take"))
        take_btn.setObjectName("PrimaryButton")
        take_btn.clicked.connect(self._take_payment)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(take_btn)
        toolbar.addWidget(refresh_btn)
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                tr("payments.paid_at"),
                tr("payments.invoice"),
                tr("payments.amount"),
                tr("payments.method"),
                tr("payments.reference"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, stretch=1)

        self._empty = QLabel(tr("payments.empty"))
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._empty)

    def refresh(self) -> None:
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            self._payments = FinanceService(db).list_payments(
                self._session.user.company_id,
                query=query,
                limit=200,
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._payments = []
        finally:
            db.close()
        self._fill()

    def _fill(self) -> None:
        self._table.setRowCount(0)
        for payment in self._payments:
            row = self._table.rowCount()
            self._table.insertRow(row)
            invoice_number = ""
            if payment.invoice is not None:
                invoice_number = payment.invoice.number
            paid = payment.paid_at.strftime("%Y-%m-%d %H:%M") if payment.paid_at else ""
            values = [
                paid,
                invoice_number,
                f"{payment.amount:,}".replace(",", " "),
                payment.method,
                payment.reference or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, payment.id)
                self._table.setItem(row, col, item)
        empty = len(self._payments) == 0
        self._empty.setVisible(empty)
        self._table.setVisible(not empty)

    def _take_payment(self) -> None:
        db = self._container.create_session()
        try:
            invoices = FinanceService(db).list_invoices(self._session.user.company_id)
            open_invoices = [
                inv
                for inv in invoices
                if inv.balance_due > 0 and inv.status not in {"draft", "void"}
            ]
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        if not open_invoices:
            QMessageBox.information(self, tr("payments.title"), tr("payments.nothing_open"))
            return

        labels = [
            f"{inv.number} — {inv.balance_due:,}".replace(",", " ") for inv in open_invoices
        ]
        choice, ok = QInputDialog.getItem(
            self,
            tr("payments.take"),
            tr("payments.select_invoice"),
            labels,
            0,
            False,
        )
        if not ok or not choice:
            return
        invoice = open_invoices[labels.index(choice)]
        dialog = PaymentFormDialog(
            self, invoice_id=invoice.id, balance_due=invoice.balance_due
        )
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
            show_toast(self, tr("payments.recorded"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
