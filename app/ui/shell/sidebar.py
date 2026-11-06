"""Application sidebar navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.localization.translator import tr


class Sidebar(QWidget):
    """Left navigation matching the UI/UX blueprint order."""

    route_selected = Signal(str)

    ROUTES: tuple[tuple[str, str], ...] = (
        ("dashboard", "nav.dashboard"),
        ("customers", "nav.customers"),
        ("companies", "nav.companies"),
        ("reception", "nav.reception"),
        ("work_orders", "nav.work_orders"),
        ("technicians", "nav.technicians"),
        ("inventory", "nav.inventory"),
        ("warehouse", "nav.warehouse"),
        ("suppliers", "nav.suppliers"),
        ("finance", "nav.finance"),
        ("payments", "nav.payments"),
        ("reports", "nav.reports"),
        ("calendar", "nav.calendar"),
        ("notifications", "nav.notifications"),
        ("telegram", "nav.telegram"),
        ("automation", "nav.automation"),
        ("ai_assistant", "nav.ai"),
        ("settings", "nav.settings"),
        ("administration", "nav.administration"),
        ("sync", "nav.sync"),
        ("help", "nav.help"),
        ("about", "nav.about"),
        ("logout", "nav.logout"),
    )

    def __init__(self) -> None:
        super().__init__(objectName="Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)
        self._list = QListWidget()
        self._list.setSpacing(1)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._base_labels: dict[str, str] = {}
        for route_id, label_key in self.ROUTES:
            base = tr(label_key)
            self._base_labels[route_id] = base
            item = QListWidgetItem(base)
            item.setData(Qt.ItemDataRole.UserRole, route_id)
            if route_id == "logout":
                item.setForeground(QColor("#8A3B32"))
            self._list.addItem(item)
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)
        self._list.setCurrentRow(0)

    def _on_row_changed(self, row: int) -> None:
        item = self._list.item(row)
        if item is None:
            return
        route_id = item.data(Qt.ItemDataRole.UserRole)
        if route_id:
            self.route_selected.emit(route_id)

    def select_route(self, route_id: str) -> None:
        """Highlight a route without re-emitting if already selected."""
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == route_id:
                if self._list.currentRow() == row:
                    return
                self._list.blockSignals(True)
                self._list.setCurrentRow(row)
                self._list.blockSignals(False)
                return

    def set_badge(self, route_id: str, count: int) -> None:
        """Show unread count next to a sidebar route (0 clears badge)."""
        base = self._base_labels.get(route_id)
        if base is None:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None or item.data(Qt.ItemDataRole.UserRole) != route_id:
                continue
            if count > 0:
                item.setText(f"{base} ({count})")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            else:
                item.setText(base)
                font = QFont(item.font())
                font.setBold(False)
                item.setFont(font)
            return

    def apply_allowed_routes(self, allowed: set[str]) -> None:
        """Hide routes the user cannot access (logout always kept)."""
        allowed = set(allowed) | {"logout"}
        first_visible = -1
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            route_id = item.data(Qt.ItemDataRole.UserRole)
            visible = route_id in allowed
            item.setHidden(not visible)
            if visible and first_visible < 0 and route_id != "logout":
                first_visible = row
        if first_visible >= 0 and self._list.item(self._list.currentRow()) is not None:
            current = self._list.item(self._list.currentRow())
            if current is not None and current.isHidden():
                self._list.blockSignals(True)
                self._list.setCurrentRow(first_visible)
                self._list.blockSignals(False)
