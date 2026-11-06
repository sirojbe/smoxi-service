"""Reporting service — statistics and file exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.time import utc_now
from app.modules.customers.models.customer import Customer
from app.modules.finance.models.enums import InvoiceStatus
from app.modules.finance.models.invoice import Invoice, Payment
from app.modules.inventory.models.item import InventoryItem
from app.modules.work_orders.models.status import WorkOrderStatus, status_label
from app.modules.work_orders.models.work_order import WorkOrder


@dataclass(frozen=True)
class DashboardStats:
    """KPI snapshot for dashboard and reports."""

    today_received: int
    waiting_count: int
    completed_today: int
    revenue_today: int
    open_work_orders: int
    low_stock_items: int
    customers_total: int
    expense_today: int = 0
    ready_count: int = 0
    approval_waiting: int = 0


@dataclass(frozen=True)
class WorkOrderReportRow:
    """One work order line in a period report."""

    number: str
    status: str
    status_label: str
    customer_name: str
    phone: str
    problem: str
    estimated_cost: int
    expense_total: int
    received_at: datetime
    delivered_at: datetime | None = None


@dataclass(frozen=True)
class PeriodReport:
    """Aggregated report for a date range."""

    from_date: datetime
    to_date: datetime
    work_orders_created: int
    work_orders_delivered: int
    invoices_issued: int
    payments_total: int
    revenue_total: int
    expense_total: int = 0
    customers_served: int = 0
    ready_count: int = 0
    approval_waiting: int = 0
    work_orders: list[WorkOrderReportRow] = field(default_factory=list)


WAITING_STATUSES = (
    WorkOrderStatus.RECEIVED.value,
    WorkOrderStatus.WAITING_DIAGNOSIS.value,
    WorkOrderStatus.DIAGNOSING.value,
    WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
    WorkOrderStatus.APPROVED.value,
    WorkOrderStatus.WAITING_PARTS.value,
    WorkOrderStatus.REPAIRING.value,
    WorkOrderStatus.TESTING.value,
    WorkOrderStatus.QUALITY_CHECK.value,
    WorkOrderStatus.READY.value,
)


class ReportService:
    """Build operational/financial reports and export files."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def dashboard_stats(self, company_id: int) -> DashboardStats:
        """Return current KPI counters."""
        now = utc_now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_received = self._count_wo(company_id, received_from=day_start)
        waiting = self._count_wo(company_id, statuses=WAITING_STATUSES)
        completed = self._count_wo(
            company_id,
            statuses=(WorkOrderStatus.DELIVERED.value, WorkOrderStatus.CLOSED.value),
            delivered_from=day_start,
        )
        revenue = self._sum_payments(company_id, paid_from=day_start)
        open_wo = self._count_wo(company_id, statuses=WAITING_STATUSES)
        low_stock = self._session.scalar(
            select(func.count())
            .select_from(InventoryItem)
            .where(
                InventoryItem.company_id == company_id,
                InventoryItem.deleted_at.is_(None),
                InventoryItem.quantity_on_hand <= InventoryItem.min_quantity,
            )
        )
        customers = self._session.scalar(
            select(func.count())
            .select_from(Customer)
            .where(Customer.company_id == company_id, Customer.deleted_at.is_(None))
        )
        expense_today = self._session.scalar(
            select(func.coalesce(func.sum(WorkOrder.expense_total), 0)).where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.received_at >= day_start,
            )
        )
        ready_count = self._count_wo(
            company_id, statuses=(WorkOrderStatus.READY.value,)
        )
        approval_waiting = self._count_wo(
            company_id,
            statuses=(WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,),
        )
        return DashboardStats(
            today_received=int(today_received or 0),
            waiting_count=int(waiting or 0),
            completed_today=int(completed or 0),
            revenue_today=int(revenue or 0),
            open_work_orders=int(open_wo or 0),
            low_stock_items=int(low_stock or 0),
            customers_total=int(customers or 0),
            expense_today=int(expense_today or 0),
            ready_count=int(ready_count or 0),
            approval_waiting=int(approval_waiting or 0),
        )

    def period_report(
        self,
        company_id: int,
        *,
        days: int | None = 30,
        from_day: date | None = None,
        to_day: date | None = None,
    ) -> PeriodReport:
        """Return aggregated report for a date range (or last *days*)."""
        from_date, to_date = self._resolve_range(days=days, from_day=from_day, to_day=to_day)
        created = self._count_wo(company_id, received_from=from_date, received_to=to_date)
        delivered = self._count_wo(
            company_id,
            statuses=(WorkOrderStatus.DELIVERED.value, WorkOrderStatus.CLOSED.value),
            delivered_from=from_date,
            delivered_to=to_date,
        )
        invoices = self._session.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.company_id == company_id,
                Invoice.deleted_at.is_(None),
                Invoice.status != InvoiceStatus.VOID.value,
                Invoice.created_at >= from_date,
                Invoice.created_at <= to_date,
            )
        )
        payments_total = self._session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(
                Payment.company_id == company_id,
                Payment.deleted_at.is_(None),
                Payment.paid_at >= from_date,
                Payment.paid_at <= to_date,
            )
        )
        revenue = self._sum_payments(company_id, paid_from=from_date, paid_to=to_date)
        expense = self._session.scalar(
            select(func.coalesce(func.sum(WorkOrder.expense_total), 0)).where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.received_at >= from_date,
                WorkOrder.received_at <= to_date,
            )
        )
        customers_served = self._session.scalar(
            select(func.count(func.distinct(WorkOrder.customer_id))).where(
                WorkOrder.company_id == company_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.received_at >= from_date,
                WorkOrder.received_at <= to_date,
            )
        )
        ready_count = self._count_wo(
            company_id,
            statuses=(WorkOrderStatus.READY.value,),
            received_from=from_date,
            received_to=to_date,
        )
        approval_waiting = self._count_wo(
            company_id,
            statuses=(WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,),
            received_from=from_date,
            received_to=to_date,
        )
        work_orders = self._work_order_rows(company_id, from_date, to_date)
        return PeriodReport(
            from_date=from_date,
            to_date=to_date,
            work_orders_created=int(created or 0),
            work_orders_delivered=int(delivered or 0),
            invoices_issued=int(invoices or 0),
            payments_total=int(payments_total or 0),
            revenue_total=int(revenue or 0),
            expense_total=int(expense or 0),
            customers_served=int(customers_served or 0),
            ready_count=int(ready_count or 0),
            approval_waiting=int(approval_waiting or 0),
            work_orders=work_orders,
        )

    def export_excel(
        self,
        company_id: int,
        path: Path,
        *,
        days: int | None = 30,
        from_day: date | None = None,
        to_day: date | None = None,
    ) -> Path:
        """Export period report and work orders to Excel."""
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise AppError(
                "Excel eksport uchun openpyxl o‘rnatilmagan. "
                "pip install -r requirements/base.txt"
            ) from exc

        report = self.period_report(
            company_id, days=days, from_day=from_day, to_day=to_day
        )
        wb = Workbook()
        summary = wb.active
        summary.title = "Xulosa"
        summary.append(["Koʻrsatkich", "Qiymat"])
        summary.append(
            ["Davr", f"{report.from_date.date()} — {report.to_date.date()}"]
        )
        summary.append(["Yaratilgan WO", report.work_orders_created])
        summary.append(["Topshirilgan WO", report.work_orders_delivered])
        summary.append(["Tayyor", report.ready_count])
        summary.append(["Tasdiq kutilmoqda", report.approval_waiting])
        summary.append(["Mijozlar", report.customers_served])
        summary.append(["Hisob-fakturalar", report.invoices_issued])
        summary.append(["Toʻlovlar soni", report.payments_total])
        summary.append(["Daromad (soʻm)", report.revenue_total])
        summary.append(["Xarajat (soʻm)", report.expense_total])

        sheet = wb.create_sheet("Ish buyurtmalari")
        sheet.append(
            [
                "Raqam",
                "Status",
                "Mijoz",
                "Telefon",
                "Nosozlik",
                "Narx",
                "Xarajat",
                "Qabul sanasi",
                "Topshirilgan",
            ]
        )
        for order in report.work_orders:
            sheet.append(
                [
                    order.number,
                    order.status_label,
                    order.customer_name,
                    order.phone,
                    order.problem,
                    order.estimated_cost,
                    order.expense_total,
                    order.received_at.strftime("%Y-%m-%d %H:%M"),
                    (
                        order.delivered_at.strftime("%Y-%m-%d %H:%M")
                        if order.delivered_at
                        else ""
                    ),
                ]
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(path)
        return path

    def export_pdf(
        self,
        company_id: int,
        path: Path,
        *,
        days: int | None = 30,
        from_day: date | None = None,
        to_day: date | None = None,
    ) -> Path:
        """Export a simple A4 PDF summary report."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise AppError(
                "PDF eksport uchun reportlab o‘rnatilmagan. "
                "pip install -r requirements/base.txt"
            ) from exc

        report = self.period_report(
            company_id, days=days, from_day=from_day, to_day=to_day
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(path), pagesize=A4)
        _width, height = A4
        y = height - 50
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, y, "SMOXI Service - Hisobot")
        y -= 30
        pdf.setFont("Helvetica", 11)
        lines = [
            f"Davr: {report.from_date.date()} - {report.to_date.date()}",
            f"Yaratilgan ish buyurtmalari: {report.work_orders_created}",
            f"Topshirilgan: {report.work_orders_delivered}",
            f"Tayyor: {report.ready_count}",
            f"Mijozlar: {report.customers_served}",
            f"Hisob-fakturalar: {report.invoices_issued}",
            f"To'lovlar soni: {report.payments_total}",
            f"Daromad: {report.revenue_total} so'm",
            f"Xarajat: {report.expense_total} so'm",
        ]
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 18
        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Ish buyurtmalari")
        y -= 18
        pdf.setFont("Helvetica", 9)
        for order in report.work_orders[:40]:
            if y < 60:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 9)
            line = (
                f"{order.number} | {order.status_label} | {order.customer_name} | "
                f"{order.estimated_cost}"
            )
            pdf.drawString(50, y, line[:110])
            y -= 14
        pdf.showPage()
        pdf.save()
        return path

    def _resolve_range(
        self,
        *,
        days: int | None,
        from_day: date | None,
        to_day: date | None,
    ) -> tuple[datetime, datetime]:
        if from_day is not None and to_day is not None:
            if to_day < from_day:
                from_day, to_day = to_day, from_day
            start = datetime.combine(from_day, time.min)
            end = datetime.combine(to_day, time.max)
            return start, end
        span = days if days is not None else 30
        to_date = utc_now()
        from_date = to_date - timedelta(days=span)
        return from_date, to_date

    def _work_order_rows(
        self,
        company_id: int,
        from_date: datetime,
        to_date: datetime,
    ) -> list[WorkOrderReportRow]:
        """Rows received or delivered in the period (delivered first)."""
        from sqlalchemy import or_

        orders = list(
            self._session.scalars(
                select(WorkOrder)
                .where(
                    WorkOrder.company_id == company_id,
                    WorkOrder.deleted_at.is_(None),
                    or_(
                        (WorkOrder.received_at >= from_date)
                        & (WorkOrder.received_at <= to_date),
                        (WorkOrder.delivered_at.is_not(None))
                        & (WorkOrder.delivered_at >= from_date)
                        & (WorkOrder.delivered_at <= to_date),
                    ),
                )
                .order_by(
                    WorkOrder.delivered_at.is_(None),
                    WorkOrder.delivered_at.desc(),
                    WorkOrder.received_at.desc(),
                )
                .limit(1000)
            )
        )
        customer_ids = {o.customer_id for o in orders}
        customers: dict[int, Customer] = {}
        if customer_ids:
            for customer in self._session.scalars(
                select(Customer).where(Customer.id.in_(customer_ids))
            ):
                customers[customer.id] = customer
        rows: list[WorkOrderReportRow] = []
        for order in orders:
            customer = customers.get(order.customer_id)
            rows.append(
                WorkOrderReportRow(
                    number=order.number,
                    status=order.status,
                    status_label=status_label(order.status),
                    customer_name=customer.display_name if customer else "—",
                    phone=customer.phone if customer else "—",
                    problem=(order.problem_description or "")[:120],
                    estimated_cost=int(order.estimated_cost or 0),
                    expense_total=int(order.expense_total or 0),
                    received_at=order.received_at,
                    delivered_at=order.delivered_at,
                )
            )
        return rows

    def _count_wo(
        self,
        company_id: int,
        *,
        statuses: tuple[str, ...] | None = None,
        received_from: datetime | None = None,
        received_to: datetime | None = None,
        delivered_from: datetime | None = None,
        delivered_to: datetime | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.company_id == company_id, WorkOrder.deleted_at.is_(None))
        )
        if statuses:
            stmt = stmt.where(WorkOrder.status.in_(statuses))
        if received_from is not None:
            stmt = stmt.where(WorkOrder.received_at >= received_from)
        if received_to is not None:
            stmt = stmt.where(WorkOrder.received_at <= received_to)
        if delivered_from is not None:
            stmt = stmt.where(WorkOrder.delivered_at >= delivered_from)
        if delivered_to is not None:
            stmt = stmt.where(WorkOrder.delivered_at <= delivered_to)
        return int(self._session.scalar(stmt) or 0)

    def _sum_payments(
        self,
        company_id: int,
        *,
        paid_from: datetime | None = None,
        paid_to: datetime | None = None,
    ) -> int:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id, Payment.deleted_at.is_(None)
        )
        if paid_from is not None:
            stmt = stmt.where(Payment.paid_at >= paid_from)
        if paid_to is not None:
            stmt = stmt.where(Payment.paid_at <= paid_to)
        return int(self._session.scalar(stmt) or 0)
