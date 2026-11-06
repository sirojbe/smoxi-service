"""Reports page with date range and full period details."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
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
from app.modules.cx.services.kpi_service import TechnicianKpiService
from app.modules.reports.services.report_service import ReportService


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


class ReportsPage(QWidget):
    """Operational and financial summary reports."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("reports.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("reports.subtitle")))

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel(tr("reports.from_date")))
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDisplayFormat("dd.MM.yyyy")
        today = QDate.currentDate()
        self._from.setDate(today.addDays(-30))
        self._from.dateChanged.connect(self.refresh)
        period_row.addWidget(self._from)

        period_row.addWidget(QLabel(tr("reports.to_date")))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDisplayFormat("dd.MM.yyyy")
        self._to.setDate(today)
        self._to.dateChanged.connect(self.refresh)
        period_row.addWidget(self._to)

        today_btn = QPushButton(tr("reports.today"))
        today_btn.clicked.connect(self._set_today)
        week_btn = QPushButton(tr("reports.last_7"))
        week_btn.clicked.connect(lambda: self._set_last_days(7))
        month_btn = QPushButton(tr("reports.last_30"))
        month_btn.clicked.connect(lambda: self._set_last_days(30))
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        period_row.addWidget(today_btn)
        period_row.addWidget(week_btn)
        period_row.addWidget(month_btn)
        period_row.addWidget(refresh_btn)
        period_row.addStretch()
        root.addLayout(period_row)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        root.addWidget(self._summary)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            [
                tr("work_orders.number"),
                tr("work_orders.status"),
                tr("work_orders.customer"),
                tr("customers.phone"),
                tr("work_orders.problem"),
                tr("reports.amount"),
                tr("reports.expense"),
                tr("reports.delivered_at"),
            ]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

        root.addWidget(QLabel(tr("cx.kpi_heading"), objectName="SectionTitle"))
        self._kpi_table = QTableWidget(0, 6)
        self._kpi_table.setHorizontalHeaderLabels(
            [
                tr("cx.kpi_name"),
                tr("cx.kpi_assigned"),
                tr("cx.kpi_completed"),
                tr("cx.kpi_ready"),
                tr("cx.kpi_revenue"),
                tr("cx.kpi_score"),
            ]
        )
        self._kpi_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._kpi_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._kpi_table.horizontalHeader().setStretchLastSection(True)
        self._kpi_table.setMaximumHeight(220)
        root.addWidget(self._kpi_table)

        buttons = QHBoxLayout()
        excel_btn = QPushButton(tr("reports.export_excel"))
        excel_btn.setObjectName("PrimaryButton")
        excel_btn.clicked.connect(self._export_excel)
        pdf_btn = QPushButton(tr("reports.export_pdf"))
        pdf_btn.clicked.connect(self._export_pdf)
        buttons.addWidget(excel_btn)
        buttons.addWidget(pdf_btn)
        buttons.addStretch()
        root.addLayout(buttons)
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt API
        super().showEvent(event)
        self.refresh()

    def _selected_dates(self) -> tuple[date, date]:
        from_day = date(
            self._from.date().year(),
            self._from.date().month(),
            self._from.date().day(),
        )
        to_day = date(
            self._to.date().year(),
            self._to.date().month(),
            self._to.date().day(),
        )
        return from_day, to_day

    def _set_today(self) -> None:
        today = QDate.currentDate()
        self._from.blockSignals(True)
        self._to.blockSignals(True)
        self._from.setDate(today)
        self._to.setDate(today)
        self._from.blockSignals(False)
        self._to.blockSignals(False)
        self.refresh()

    def _set_last_days(self, days: int) -> None:
        today = QDate.currentDate()
        self._from.blockSignals(True)
        self._to.blockSignals(True)
        self._from.setDate(today.addDays(-(days - 1)))
        self._to.setDate(today)
        self._from.blockSignals(False)
        self._to.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        from_day, to_day = self._selected_dates()
        db = self._container.create_session()
        try:
            report = ReportService(db).period_report(
                self._session.user.company_id,
                days=None,
                from_day=from_day,
                to_day=to_day,
            )
            text = (
                f"{tr('reports.period')}: {report.from_date.date()} — {report.to_date.date()}\n"
                f"{tr('reports.wo_created')}: {report.work_orders_created}  ·  "
                f"{tr('reports.wo_delivered')}: {report.work_orders_delivered}  ·  "
                f"{tr('reports.ready')}: {report.ready_count}  ·  "
                f"{tr('reports.customers')}: {report.customers_served}\n"
                f"{tr('reports.invoices')}: {report.invoices_issued}  ·  "
                f"{tr('reports.payments')}: {report.payments_total}  ·  "
                f"{tr('reports.revenue')}: {_money(report.revenue_total)} soʻm  ·  "
                f"{tr('reports.expense')}: {_money(report.expense_total)} soʻm"
            )
            self._summary.setText(text)
            self._table.setRowCount(0)
            for order in report.work_orders:
                row = self._table.rowCount()
                self._table.insertRow(row)
                delivered = (
                    order.delivered_at.strftime("%d.%m.%Y %H:%M")
                    if order.delivered_at
                    else "—"
                )
                values = [
                    order.number,
                    order.status_label,
                    order.customer_name,
                    order.phone,
                    order.problem,
                    _money(order.estimated_cost),
                    _money(order.expense_total),
                    delivered,
                ]
                for col, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    if col in {5, 6}:
                        cell.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self._table.setItem(row, col, cell)

            date_from = datetime.combine(from_day, time.min, tzinfo=UTC)
            date_to = datetime.combine(to_day, time.max, tzinfo=UTC)
            kpi_rows = TechnicianKpiService(db).leaderboard(
                self._session.user.company_id,
                date_from=date_from,
                date_to=date_to,
            )
            self._kpi_table.setRowCount(0)
            for kpi in kpi_rows:
                row = self._kpi_table.rowCount()
                self._kpi_table.insertRow(row)
                cells = [
                    kpi.full_name,
                    str(kpi.assigned),
                    str(kpi.completed),
                    str(kpi.ready),
                    _money(kpi.revenue),
                    f"{kpi.productivity_score:.0f}",
                ]
                for col, value in enumerate(cells):
                    cell = QTableWidgetItem(value)
                    if col >= 1:
                        cell.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self._kpi_table.setItem(row, col, cell)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _export_excel(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            tr("reports.export_excel"),
            "smoxi_hisobot.xlsx",
            "Excel (*.xlsx)",
        )
        if not path_str:
            return
        from_day, to_day = self._selected_dates()
        db = self._container.create_session()
        try:
            path = ReportService(db).export_excel(
                self._session.user.company_id,
                Path(path_str),
                days=None,
                from_day=from_day,
                to_day=to_day,
            )
            QMessageBox.information(
                self,
                tr("reports.title"),
                tr("reports.exported", path=str(path)),
            )
        except Exception as exc:  # noqa: BLE001 — user-facing export errors
            QMessageBox.warning(self, tr("common.error"), str(exc))
        finally:
            db.close()

    def _export_pdf(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            tr("reports.export_pdf"),
            "smoxi_hisobot.pdf",
            "PDF (*.pdf)",
        )
        if not path_str:
            return
        from_day, to_day = self._selected_dates()
        db = self._container.create_session()
        try:
            path = ReportService(db).export_pdf(
                self._session.user.company_id,
                Path(path_str),
                days=None,
                from_day=from_day,
                to_day=to_day,
            )
            QMessageBox.information(
                self,
                tr("reports.title"),
                tr("reports.exported", path=str(path)),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("common.error"), str(exc))
        finally:
            db.close()
