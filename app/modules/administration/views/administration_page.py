"""Administration page — audit trail."""

from __future__ import annotations

from PySide6.QtWidgets import (
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
from app.modules.administration.services.admin_service import AdministrationService


class AdministrationPage(QWidget):
    """System administration: audit log (read-only MVP)."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("admin.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("admin.subtitle")))

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("admin.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(refresh_btn)
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                tr("admin.when"),
                tr("admin.action"),
                tr("admin.actor"),
                tr("admin.entity"),
                tr("admin.message"),
            ]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            rows = AdministrationService(db).list_audit(
                query=self._search.text().strip() or None
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._table.setRowCount(0)
        for row, entry in enumerate(rows):
            self._table.insertRow(row)
            when = (
                entry.occurred_at.strftime("%d.%m.%Y %H:%M:%S")
                if entry.occurred_at
                else ""
            )
            entity = ""
            if entry.entity_type:
                entity = f"{entry.entity_type}:{entry.entity_id or ''}"
            values = [
                when,
                entry.action,
                str(entry.actor_id or "—"),
                entity or "—",
                (entry.message or "")[:120],
            ]
            for col, value in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(value))
