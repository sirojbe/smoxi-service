"""Desktop shell preferences (idle lock, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

ORG = "SMOXI"
APP = "SMOXIService"


@dataclass(frozen=True, slots=True)
class ShellPrefs:
    idle_lock_minutes: int = 10  # 0 = disabled


def load_shell_prefs() -> ShellPrefs:
    s = QSettings(ORG, APP)
    return ShellPrefs(
        idle_lock_minutes=max(0, int(s.value("shell/idle_lock_minutes", 10))),
    )


def save_shell_prefs(prefs: ShellPrefs) -> None:
    s = QSettings(ORG, APP)
    s.setValue("shell/idle_lock_minutes", max(0, prefs.idle_lock_minutes))
    s.sync()
