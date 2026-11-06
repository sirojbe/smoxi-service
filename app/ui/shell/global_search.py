"""Global search (Ctrl+K) — navigate to entities and routes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.customers.services.customer_service import CustomerService
from app.modules.work_orders.services.work_order_service import WorkOrderService


@dataclass(frozen=True, slots=True)
class SearchHit:
    kind: str
    title: str
    subtitle: str
    route: str
    ref: str | None = None


class GlobalSearchDialog(QDialog):
    """Command palette: routes + customers + work orders."""

    navigate_requested = Signal(str, object)  # route, ref

    def __init__(
        self,
        parent: QWidget,
        container: ServiceContainer,
        session: DesktopSession,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._session = session
        self.setWindowTitle(tr("search.title"))
        self.setMinimumSize(520, 420)
        self.setModal(True)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(tr("search.hint")))
        self._input = QLineEdit()
        self._input.setPlaceholderText(tr("search.placeholder"))
        self._input.textChanged.connect(self._search)
        self._input.returnPressed.connect(self._accept_current)
        root.addWidget(self._input)
        self._list = QListWidget()
        self._list.itemActivated.connect(lambda _i: self._accept_current())
        self._list.itemDoubleClicked.connect(lambda _i: self._accept_current())
        root.addWidget(self._list, stretch=1)
        self._hits: list[SearchHit] = []
        self._search("")
        self._input.setFocus()

    def _search(self, text: str) -> None:
        q = text.strip().lower()
        hits: list[SearchHit] = []
        routes = [
            ("dashboard", tr("nav.dashboard")),
            ("customers", tr("nav.customers")),
            ("companies", tr("nav.companies")),
            ("reception", tr("nav.reception")),
            ("work_orders", tr("nav.work_orders")),
            ("inventory", tr("nav.inventory")),
            ("warehouse", tr("nav.warehouse")),
            ("calendar", tr("nav.calendar")),
            ("notifications", tr("nav.notifications")),
            ("telegram", tr("nav.telegram")),
            ("reports", tr("nav.reports")),
            ("settings", tr("nav.settings")),
            ("administration", tr("nav.administration")),
            ("sync", tr("nav.sync")),
            ("help", tr("nav.help")),
        ]
        for route, label in routes:
            if not q or q in label.lower() or q in route:
                hits.append(
                    SearchHit(
                        kind="route",
                        title=label,
                        subtitle=tr("search.kind_route"),
                        route=route,
                    )
                )
        if len(q) >= 2:
            db = self._container.create_session()
            try:
                for c in CustomerService(db).list_customers(
                    self._session.user.company_id, query=q
                )[:15]:
                    hits.append(
                        SearchHit(
                            kind="customer",
                            title=c.display_name,
                            subtitle=c.phone,
                            route="customers",
                            ref=str(c.id),
                        )
                    )
                for wo in WorkOrderService(db).list_work_orders(
                    self._session.user.company_id, query=q
                )[:15]:
                    hits.append(
                        SearchHit(
                            kind="work_order",
                            title=wo.number,
                            subtitle=(wo.problem_description or "")[:80],
                            route="work_orders",
                            ref=str(wo.id),
                        )
                    )
            finally:
                db.close()
        self._hits = hits[:40]
        self._list.clear()
        for hit in self._hits:
            item = QListWidgetItem(f"{hit.title}\n{hit.subtitle} · {hit.kind}")
            self._list.addItem(item)
        if self._hits:
            self._list.setCurrentRow(0)

    def _accept_current(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._hits):
            return
        hit = self._hits[row]
        self.navigate_requested.emit(hit.route, hit.ref)
        self.accept()


def install_global_search_shortcut(
    window: QWidget,
    container: ServiceContainer,
    session: DesktopSession,
    on_navigate: Callable[[str, object], None],
) -> QShortcut:
    """Bind Ctrl+K on *window* to open GlobalSearchDialog."""

    def _open() -> None:
        dialog = GlobalSearchDialog(window, container, session)
        dialog.navigate_requested.connect(on_navigate)
        dialog.exec()

    shortcut = QShortcut(QKeySequence("Ctrl+K"), window)
    shortcut.activated.connect(_open)
    return shortcut
