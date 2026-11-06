"""In-app notifications center page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.notifications.services.notification_service import NotificationService

_FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "notifications.filter_all"),
    ("unread", "notifications.filter_unread"),
    ("telegram", "notifications.filter_telegram"),
    ("work_order", "notifications.filter_work_order"),
    ("system", "notifications.filter_system"),
    ("sync", "notifications.filter_sync"),
)


class NotificationsPage(QWidget):
    """List of in-app notifications with filters and open / mark-read actions."""

    open_route_requested = Signal(str, object)  # route, ref_key

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._filter = "all"
        self._ids: list[int] = []
        self._build_ui()
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("notifications.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("notifications.subtitle")))

        filter_row = QHBoxLayout()
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        for idx, (code, key) in enumerate(_FILTERS):
            btn = QPushButton(tr(key))
            btn.setCheckable(True)
            btn.setChecked(code == "all")
            btn.clicked.connect(lambda _c=False, c=code: self._set_filter(c))
            self._filter_group.addButton(btn, idx)
            filter_row.addWidget(btn)
        filter_row.addStretch()
        root.addLayout(filter_row)

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        read_all_btn = QPushButton(tr("notifications.mark_all_read"))
        read_all_btn.clicked.connect(self._mark_all_read)
        open_btn = QPushButton(tr("notifications.open"))
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(self._open_selected)
        prefs_btn = QPushButton(tr("notifications.preferences"))
        prefs_btn.clicked.connect(
            lambda: self.open_route_requested.emit("settings", None)
        )
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(read_all_btn)
        toolbar.addWidget(prefs_btn)
        toolbar.addStretch()
        toolbar.addWidget(open_btn)
        root.addLayout(toolbar)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(lambda _i: self._open_selected())
        root.addWidget(self._list, stretch=1)

        self._empty = QLabel(tr("notifications.empty"))
        self._empty.setObjectName("MutedLabel")
        root.addWidget(self._empty)

    def _set_filter(self, code: str) -> None:
        self._filter = code
        self.refresh()

    def refresh(self) -> None:
        unread_only = self._filter == "unread"
        kind = None if self._filter in {"all", "unread"} else self._filter
        db = self._container.create_session()
        try:
            rows = NotificationService(db).list_notifications(
                self._session.user.company_id,
                unread_only=unread_only,
                kind=kind,
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        self._list.clear()
        self._ids = []
        for row in rows:
            stamp = row.created_at.strftime("%d.%m %H:%M") if row.created_at else ""
            prefix = "● " if not row.is_read else "○ "
            kind_label = row.kind
            label = f"{prefix}[{kind_label}] {row.title}\n{stamp}  ·  {row.body}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, row.route)
            item.setData(Qt.ItemDataRole.UserRole + 2, row.ref_key)
            if not row.is_read:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._list.addItem(item)
            self._ids.append(row.id)
        self._empty.setVisible(len(rows) == 0)
        self._list.setVisible(len(rows) > 0)

    def _selected_meta(self) -> tuple[int | None, str | None, str | None]:
        item = self._list.currentItem()
        if item is None:
            return None, None, None
        return (
            int(item.data(Qt.ItemDataRole.UserRole)),
            item.data(Qt.ItemDataRole.UserRole + 1),
            item.data(Qt.ItemDataRole.UserRole + 2),
        )

    def _open_selected(self) -> None:
        notification_id, route, ref_key = self._selected_meta()
        if notification_id is None:
            QMessageBox.information(
                self, tr("notifications.title"), tr("notifications.select_first")
            )
            return
        db = self._container.create_session()
        try:
            NotificationService(db).mark_read(notification_id)
            db.commit()
        finally:
            db.close()
        self.refresh()
        if route:
            self.open_route_requested.emit(route, ref_key)

    def _mark_all_read(self) -> None:
        db = self._container.create_session()
        try:
            NotificationService(db).mark_all_read(self._session.user.company_id)
            db.commit()
        finally:
            db.close()
        self.refresh()
