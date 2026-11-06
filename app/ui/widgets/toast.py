"""Reusable toast helper for feature pages."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget


def show_toast(widget: QWidget, text: str, *, ms: int = 3500) -> None:
    """Show a non-blocking toast via the active MainWindow when available."""
    window = widget.window()
    show = getattr(window, "show_toast", None)
    if callable(show):
        show(text, ms=ms)
        return
    app = QApplication.instance()
    if app is None:
        return
    for top in app.topLevelWidgets():
        outer = getattr(top, "show_toast", None)
        if callable(outer):
            outer(text, ms=ms)
            return
