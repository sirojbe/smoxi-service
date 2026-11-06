"""AI Assistant page — local operator helper."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.ai_assistant.services.assistant_service import AiAssistantService


class AiAssistantPage(QWidget):
    """Chat-style local assistant with actionable suggestions."""

    navigate_requested = Signal(str)

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("ai.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("ai.subtitle")))

        self._suggestions = QListWidget()
        self._suggestions.itemClicked.connect(self._on_suggestion)
        root.addWidget(QLabel(tr("ai.suggestions")))
        root.addWidget(self._suggestions)

        self._chat = QTextEdit()
        self._chat.setReadOnly(True)
        self._chat.setMinimumHeight(180)
        root.addWidget(self._chat)

        row = QHBoxLayout()
        self._input = QTextEdit()
        self._input.setPlaceholderText(tr("ai.placeholder"))
        self._input.setMaximumHeight(70)
        send = QPushButton(tr("ai.send"))
        send.setObjectName("PrimaryButton")
        send.clicked.connect(self._ask)
        refresh = QPushButton(tr("common.refresh"))
        refresh.clicked.connect(self.refresh)
        row.addWidget(self._input, stretch=1)
        row.addWidget(send)
        row.addWidget(refresh)
        root.addLayout(row)
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            items = AiAssistantService(db).suggestions(self._session.user.company_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._suggestions.clear()
        for s in items:
            item = QListWidgetItem(f"{s.title}\n{s.detail}")
            item.setData(Qt.ItemDataRole.UserRole, s.route)
            self._suggestions.addItem(item)

    def _on_suggestion(self, item: QListWidgetItem) -> None:
        route = item.data(Qt.ItemDataRole.UserRole)
        if route:
            self.navigate_requested.emit(str(route))

    def _ask(self) -> None:
        question = self._input.toPlainText().strip()
        db = self._container.create_session()
        try:
            reply = AiAssistantService(db).ask(
                self._session.user.company_id, question
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        if question:
            self._chat.append(f"<b>Siz:</b> {question}")
        self._chat.append(f"<b>Yordamchi:</b> {reply.text}")
        self._input.clear()
        self._suggestions.clear()
        for s in reply.suggestions:
            item = QListWidgetItem(f"{s.title}\n{s.detail}")
            item.setData(Qt.ItemDataRole.UserRole, s.route)
            self._suggestions.addItem(item)
