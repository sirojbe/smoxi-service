"""Toast notification overlay for the main window."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class ToastBanner(QFrame):
    """Non-blocking toast shown at the bottom-right of the workspace."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ToastBanner")
        self.setStyleSheet(
            "#ToastBanner {"
            "background:#1F4E79;color:#FFFFFF;border-radius:8px;"
            "padding:10px 16px;}"
            "#ToastBanner QLabel { color:#FFFFFF; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self._label = QLabel("")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, *, ms: int = 3500) -> None:
        self._label.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            self.setFixedWidth(min(420, parent.width() - 40))
            self.move(
                parent.width() - self.width() - 24,
                parent.height() - self.height() - 24,
            )
        self.show()
        self.raise_()
        self._timer.start(ms)
