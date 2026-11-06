"""Help page — topics, shortcuts, support."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.localization.translator import tr

_TOPICS: tuple[tuple[str, str, str], ...] = (
    (
        "help.topic_start",
        "qabul login telegram",
        "help.body_start",
    ),
    (
        "help.topic_wo",
        "buyurtma status tayyor",
        "help.body_wo",
    ),
    (
        "help.topic_inventory",
        "ombor zaxira",
        "help.body_inventory",
    ),
    (
        "help.topic_telegram",
        "telegram bot mini app",
        "help.body_telegram",
    ),
    (
        "help.topic_shortcuts",
        "klaviatura ctrl shortcut",
        "help.body_shortcuts",
    ),
    (
        "help.topic_sync",
        "sinxron sync api",
        "help.body_sync",
    ),
    (
        "help.topic_support",
        "yordam support aloqa",
        "help.body_support",
    ),
)


class HelpPage(QWidget):
    """Searchable help topics and shortcut cheat-sheet."""

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("help.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("help.subtitle")))

        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("help.search_placeholder"))
        self._search.textChanged.connect(self._filter)
        root.addWidget(self._search)

        row = QHBoxLayout()
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._show_topic)
        self._body = QTextBrowser()
        self._body.setOpenExternalLinks(True)
        row.addWidget(self._list, stretch=1)
        row.addWidget(self._body, stretch=2)
        root.addLayout(row, stretch=1)
        self._reload_list()

    def _reload_list(self, query: str = "") -> None:
        q = query.strip().lower()
        self._list.clear()
        self._visible: list[tuple[str, str]] = []
        for title_key, keywords, body_key in _TOPICS:
            title = tr(title_key)
            hay = f"{title} {keywords} {tr(body_key)}".lower()
            if q and q not in hay:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, body_key)
            self._list.addItem(item)
            self._visible.append((title, body_key))
        if self._list.count():
            self._list.setCurrentRow(0)

    def _filter(self, text: str) -> None:
        self._reload_list(text)

    def _show_topic(self, row: int) -> None:
        if row < 0:
            self._body.clear()
            return
        item = self._list.item(row)
        if item is None:
            return
        body_key = item.data(Qt.ItemDataRole.UserRole)
        self._body.setHtml(f"<h2>{item.text()}</h2><p>{tr(str(body_key))}</p>")
