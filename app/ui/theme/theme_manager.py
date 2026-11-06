"""Application theme management."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.config.settings import PROJECT_ROOT
from app.core.enums import ThemeMode

_THEME_DIR = PROJECT_ROOT / "app" / "ui" / "theme"


class ThemeManager:
    """Apply light/dark stylesheets to the Qt application."""

    def __init__(self) -> None:
        self._mode = ThemeMode.SYSTEM

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    def apply(self, app: QApplication, mode: ThemeMode | str) -> None:
        """Apply the requested theme to *app*."""
        if isinstance(mode, str):
            mode = ThemeMode(mode)
        self._mode = mode
        resolved = self._resolve_mode(mode)
        stylesheet = self._load_stylesheet(resolved)
        app.setStyleSheet(stylesheet)

    def toggle(self, app: QApplication) -> ThemeMode:
        """Flip between light and dark (resolves SYSTEM first)."""
        resolved = self._resolve_mode(self._mode)
        next_mode = ThemeMode.LIGHT if resolved == ThemeMode.DARK else ThemeMode.DARK
        self.apply(app, next_mode)
        return next_mode

    def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
        if mode != ThemeMode.SYSTEM:
            return mode
        app = QApplication.instance()
        if app is None:
            return ThemeMode.LIGHT
        palette = app.palette()
        window_color = palette.window().color()
        return ThemeMode.DARK if window_color.lightness() < 128 else ThemeMode.LIGHT

    def _load_stylesheet(self, mode: ThemeMode) -> str:
        filename = "dark.qss" if mode == ThemeMode.DARK else "light.qss"
        path = _THEME_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
