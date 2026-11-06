"""Telegram inbox page — customer ↔ staff chat."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.telegram.schemas import TelegramReplySchema
from app.modules.telegram.services.chat_service import TelegramChatService


class TelegramPage(QWidget):
    """Two-pane Telegram inbox with reply."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._current_chat_id: str | None = None
        self._threads_by_row: list[str] = []
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(4000)
        self._timer.timeout.connect(self._soft_refresh)
        self._timer.start()
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt API
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()
        self.refresh()

    def hideEvent(self, event) -> None:  # noqa: N802 — Qt API
        super().hideEvent(event)
        self._timer.stop()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("telegram.title"), objectName="PageTitle"))

        self._status = QLabel("")
        self._status.setObjectName("MutedLabel")
        root.addWidget(self._status)

        self._unread_banner = QLabel("")
        self._unread_banner.setObjectName("SuccessBanner")
        self._unread_banner.setWordWrap(True)
        self._unread_banner.hide()
        root.addWidget(self._unread_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel(tr("telegram.threads")))
        self._threads = QListWidget()
        self._threads.currentRowChanged.connect(self._on_thread_selected)
        left_layout.addWidget(self._threads)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        left_layout.addWidget(refresh_btn)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_title = QLabel(tr("telegram.select_thread"))
        right_layout.addWidget(self._chat_title)
        self._messages = QTextEdit()
        self._messages.setReadOnly(True)
        right_layout.addWidget(self._messages, stretch=1)

        reply_row = QHBoxLayout()
        self._reply = QTextEdit()
        self._reply.setPlaceholderText(tr("telegram.reply_placeholder"))
        self._reply.setMaximumHeight(90)
        send_btn = QPushButton(tr("telegram.send"))
        send_btn.setObjectName("PrimaryButton")
        send_btn.clicked.connect(self._send_reply)
        reply_row.addWidget(self._reply, stretch=1)
        reply_row.addWidget(send_btn)
        right_layout.addLayout(reply_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

    def refresh(self) -> None:
        company_id = self._session.user.company_id
        db = self._container.create_session()
        try:
            service = TelegramChatService(db)
            configured, detail = service.connection_status(company_id)
            if not configured:
                self._status.setText(tr("telegram.status_no_token"))
            elif detail == "configured":
                self._status.setText(tr("telegram.status_ok"))
            else:
                self._status.setText(tr("telegram.status_bot", username=detail))
            threads = service.list_threads(company_id)
            unread_total = service.count_unread(company_id)
        finally:
            db.close()

        if unread_total > 0:
            self._unread_banner.setText(tr("telegram.unread_banner", count=unread_total))
            self._unread_banner.show()
        else:
            self._unread_banner.hide()

        selected = self._current_chat_id
        self._threads.blockSignals(True)
        self._threads.clear()
        self._threads_by_row = []
        restore_row = -1
        for index, thread in enumerate(threads):
            if thread.unread_count:
                label = tr(
                    "telegram.thread_unread",
                    name=thread.customer_name,
                    count=thread.unread_count,
                    preview=thread.last_body,
                )
            else:
                label = f"{thread.customer_name}\n{thread.last_body}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, thread.chat_id)
            if thread.unread_count:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._threads.addItem(item)
            self._threads_by_row.append(thread.chat_id)
            if selected and thread.chat_id == selected:
                restore_row = index
        self._threads.blockSignals(False)
        if restore_row >= 0:
            self._threads.setCurrentRow(restore_row)
        elif self._current_chat_id:
            self._load_messages(self._current_chat_id)

    def open_chat(self, chat_id: str) -> None:
        """Open a conversation by Telegram chat id (from notification)."""
        self._current_chat_id = str(chat_id)
        self.refresh()
        if chat_id in self._threads_by_row:
            self._threads.setCurrentRow(self._threads_by_row.index(chat_id))
        else:
            self._load_messages(str(chat_id))

    def _soft_refresh(self) -> None:
        if self.isVisible():
            self.refresh()

    def _on_thread_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._threads_by_row):
            return
        chat_id = self._threads_by_row[row]
        self._current_chat_id = chat_id
        self._load_messages(chat_id)

    def _load_messages(self, chat_id: str) -> None:
        company_id = self._session.user.company_id
        db = self._container.create_session()
        try:
            service = TelegramChatService(db)
            service.mark_read(company_id, chat_id)
            messages = service.list_messages(company_id, chat_id)
            customer = None
            for thread in service.list_threads(company_id):
                if thread.chat_id == chat_id:
                    customer = thread
                    break
            db.commit()
        finally:
            db.close()

        if customer is not None:
            self._chat_title.setText(
                tr(
                    "telegram.chat_with",
                    name=customer.customer_name,
                    phone=customer.customer_phone or "—",
                )
            )
        else:
            self._chat_title.setText(tr("telegram.chat_id", chat_id=chat_id))

        lines: list[str] = []
        for msg in messages:
            who = tr("telegram.customer") if msg.direction == "inbound" else tr("telegram.staff")
            if msg.is_auto:
                who = tr("telegram.auto")
            stamp = msg.created_at.strftime("%d.%m %H:%M") if msg.created_at else ""
            lines.append(f"[{stamp}] {who}:\n{msg.body}\n")
        self._messages.setPlainText("\n".join(lines) if lines else tr("telegram.empty"))

    def _send_reply(self) -> None:
        if not self._current_chat_id:
            QMessageBox.information(self, tr("telegram.title"), tr("telegram.select_thread"))
            return
        body = self._reply.toPlainText().strip()
        if not body:
            return
        db = self._container.create_session()
        try:
            TelegramChatService(db).reply(
                self._session.user.company_id,
                TelegramReplySchema(chat_id=self._current_chat_id, body=body),
                actor_id=self._session.user_id,
            )
            db.commit()
        except (AppError, PydanticValidationError) as exc:
            db.rollback()
            message = getattr(exc, "message", None) or str(exc)
            QMessageBox.warning(self, tr("common.error"), message)
            return
        finally:
            db.close()
        self._reply.clear()
        self._load_messages(self._current_chat_id)
        self.refresh()
