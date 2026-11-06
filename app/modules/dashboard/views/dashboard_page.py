"""Dashboard home page with live KPIs and notifications snippet."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.reports.services.report_service import ReportService


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


class DashboardPage(QWidget):
    """Operational overview with live KPI cards and quick actions."""

    navigate_requested = Signal(str)

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._value_labels: dict[str, QLabel] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel(tr("dashboard.title"), objectName="PageTitle")
        welcome = QLabel(tr("dashboard.welcome", name=session.display_name))
        welcome.setObjectName("PageSubtitle")
        header.addWidget(title)
        header.addWidget(welcome)
        header_row.addLayout(header, stretch=1)
        refresh = QPushButton(tr("common.refresh"))
        refresh.setObjectName("PrimaryButton")
        refresh.clicked.connect(self.refresh)
        header_row.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        actions = QHBoxLayout()
        reception_btn = QPushButton(tr("dashboard.quick_reception"))
        reception_btn.setObjectName("AccentButton")
        reception_btn.clicked.connect(lambda: self.navigate_requested.emit("reception"))
        wo_btn = QPushButton(tr("dashboard.quick_work_orders"))
        wo_btn.clicked.connect(lambda: self.navigate_requested.emit("work_orders"))
        notif_btn = QPushButton(tr("dashboard.quick_notifications"))
        notif_btn.clicked.connect(lambda: self.navigate_requested.emit("notifications"))
        cal_btn = QPushButton(tr("dashboard.quick_calendar"))
        cal_btn.clicked.connect(lambda: self.navigate_requested.emit("calendar"))
        actions.addWidget(reception_btn)
        actions.addWidget(wo_btn)
        actions.addWidget(notif_btn)
        actions.addWidget(cal_btn)
        actions.addStretch()
        layout.addLayout(actions)

        grid = QGridLayout()
        grid.setSpacing(14)
        cards = [
            ("dashboard.kpi.today_repairs", "primary"),
            ("dashboard.kpi.approval", "warning"),
            ("dashboard.kpi.ready", "success"),
            ("dashboard.kpi.waiting", "info"),
            ("dashboard.kpi.completed", "success"),
            ("dashboard.kpi.revenue", "primary"),
            ("dashboard.kpi.expense", "danger"),
            ("dashboard.kpi.low_stock", "warning"),
        ]
        for index, (label_key, tone) in enumerate(cards):
            card, value_label = self._create_kpi_card(label_key, tone)
            self._value_labels[label_key] = value_label
            grid.addWidget(card, index // 4, index % 4)
        layout.addLayout(grid)

        layout.addWidget(QLabel(tr("dashboard.notifications_heading")))
        self._notif_list = QListWidget()
        self._notif_list.setMaximumHeight(160)
        self._notif_list.itemClicked.connect(
            lambda _i: self.navigate_requested.emit("notifications")
        )
        layout.addWidget(self._notif_list)
        layout.addStretch()
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt API
        super().showEvent(event)
        self.refresh()

    def _create_kpi_card(self, label_key: str, tone: str) -> tuple[QWidget, QLabel]:
        card = QWidget(objectName="KpiCard")
        card.setProperty("tone", tone)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        value_label = QLabel("—", objectName="KpiValue")
        text_label = QLabel(tr(label_key), objectName="KpiLabel")
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(value_label)
        card_layout.addWidget(text_label)
        return card, value_label

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            stats = ReportService(db).dashboard_stats(self._session.user.company_id)
            mapping = {
                "dashboard.kpi.today_repairs": str(stats.today_received),
                "dashboard.kpi.approval": str(stats.approval_waiting),
                "dashboard.kpi.ready": str(stats.ready_count),
                "dashboard.kpi.waiting": str(stats.waiting_count),
                "dashboard.kpi.completed": str(stats.completed_today),
                "dashboard.kpi.revenue": _money(stats.revenue_today),
                "dashboard.kpi.expense": _money(stats.expense_today),
                "dashboard.kpi.low_stock": str(stats.low_stock_items),
            }
            for key, value in mapping.items():
                label = self._value_labels.get(key)
                if label is not None:
                    label.setText(value)

            rows = NotificationService(db).list_notifications(
                self._session.user.company_id, unread_only=True
            )[:5]
            self._notif_list.clear()
            if not rows:
                self._notif_list.addItem(tr("dashboard.notifications_empty"))
            else:
                for row in rows:
                    stamp = (
                        row.created_at.strftime("%d.%m %H:%M") if row.created_at else ""
                    )
                    item = QListWidgetItem(f"● {row.title}  ·  {stamp}")
                    self._notif_list.addItem(item)
        except AppError:
            for label in self._value_labels.values():
                label.setText("—")
        finally:
            db.close()
