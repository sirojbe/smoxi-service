"""Application-wide idle activity tracker for auto-lock."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication


class IdleLockWatcher(QObject):
    """Emit ``idle_timeout`` after *minutes* of no user input (0 disables)."""

    idle_timeout = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.idle_timeout.emit)
        self._minutes = 0
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def set_idle_minutes(self, minutes: int) -> None:
        self._minutes = max(0, minutes)
        self.reset()

    def reset(self) -> None:
        self._timer.stop()
        if self._minutes > 0:
            self._timer.start(self._minutes * 60_000)

    def pause(self) -> None:
        self._timer.stop()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        et = event.type()
        if et in {
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
        }:
            if self._minutes > 0 and self._timer.isActive():
                self._timer.start(self._minutes * 60_000)
            elif self._minutes > 0 and not self._timer.isActive():
                self.reset()
        return super().eventFilter(obj, event)
