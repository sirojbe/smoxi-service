"""Sync conflicts / pending review page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api.schemas import SyncAckItem
from app.core.container import ServiceContainer
from app.core.enums import SyncStatus
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.sync.services.sync_service import SyncService


class SyncPage(QWidget):
    """Review pending / conflict entities and mark synced or conflict."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._rows: list = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("sync.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("sync.subtitle")))

        toolbar = QHBoxLayout()
        refresh = QPushButton(tr("common.refresh"))
        refresh.clicked.connect(self.refresh)
        mark_synced = QPushButton(tr("sync.mark_synced"))
        mark_synced.setObjectName("PrimaryButton")
        mark_synced.clicked.connect(self._mark_synced)
        mark_conflict = QPushButton(tr("sync.mark_conflict"))
        mark_conflict.clicked.connect(self._mark_conflict)
        toolbar.addWidget(refresh)
        toolbar.addWidget(mark_synced)
        toolbar.addWidget(mark_conflict)
        toolbar.addStretch()
        root.addLayout(toolbar)

        self._summary = QLabel()
        root.addWidget(self._summary)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                tr("sync.entity_type"),
                tr("sync.uuid"),
                tr("sync.status"),
                tr("sync.version"),
                tr("sync.updated"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            pull = SyncService(db).pull(self._session.user.company_id, limit=300)
            pending = SyncService(db).count_pending(self._session.user.company_id)
            self._rows = pull.entities
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._summary.setText(tr("sync.pending_count", count=pending))
        self._table.setRowCount(0)
        for row, ent in enumerate(self._rows):
            self._table.insertRow(row)
            values = [
                ent.entity_type,
                ent.uuid[:13] + "…",
                ent.sync_status,
                str(ent.version),
                ent.updated_at.strftime("%d.%m.%Y %H:%M") if ent.updated_at else "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                if ent.sync_status == SyncStatus.CONFLICT.value:
                    item.setForeground(Qt.GlobalColor.red)
                self._table.setItem(row, col, item)

    def _selected_entities(self) -> list:
        rows = self._table.selectionModel().selectedRows()
        out = []
        for r in rows:
            idx = self._table.item(r.row(), 0)
            if idx is None:
                continue
            i = int(idx.data(Qt.ItemDataRole.UserRole))
            if 0 <= i < len(self._rows):
                out.append(self._rows[i])
        return out

    def _ack(self, status: str) -> None:
        selected = self._selected_entities()
        if not selected:
            QMessageBox.information(self, tr("sync.title"), tr("sync.select_first"))
            return
        acks = [
            SyncAckItem(
                entity_type=e.entity_type,
                uuid=e.uuid,
                version=e.version,
                status=status,
            )
            for e in selected
        ]
        db = self._container.create_session()
        try:
            result = SyncService(db).push_acks(self._session.user.company_id, acks)
            db.commit()
            QMessageBox.information(
                self,
                tr("sync.title"),
                tr(
                    "sync.ack_result",
                    accepted=result.accepted,
                    conflicts=result.conflicts,
                ),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _mark_synced(self) -> None:
        self._ack(SyncStatus.SYNCED.value)

    def _mark_conflict(self) -> None:
        self._ack(SyncStatus.CONFLICT.value)
