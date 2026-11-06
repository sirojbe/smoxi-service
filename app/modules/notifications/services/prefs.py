"""Desktop notification preferences (local machine via QSettings)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from PySide6.QtCore import QSettings

ORG = "SMOXI"
APP = "SMOXIService"


@dataclass(frozen=True, slots=True)
class NotificationPrefs:
    toast_enabled: bool = True
    quiet_enabled: bool = False
    quiet_start_hour: int = 22
    quiet_end_hour: int = 7
    channel_telegram: bool = True
    channel_work_order: bool = True
    channel_system: bool = True


def load_notification_prefs() -> NotificationPrefs:
    s = QSettings(ORG, APP)
    return NotificationPrefs(
        toast_enabled=s.value("notif/toast_enabled", True, type=bool),
        quiet_enabled=s.value("notif/quiet_enabled", False, type=bool),
        quiet_start_hour=int(s.value("notif/quiet_start", 22)),
        quiet_end_hour=int(s.value("notif/quiet_end", 7)),
        channel_telegram=s.value("notif/ch_telegram", True, type=bool),
        channel_work_order=s.value("notif/ch_work_order", True, type=bool),
        channel_system=s.value("notif/ch_system", True, type=bool),
    )


def save_notification_prefs(prefs: NotificationPrefs) -> None:
    s = QSettings(ORG, APP)
    s.setValue("notif/toast_enabled", prefs.toast_enabled)
    s.setValue("notif/quiet_enabled", prefs.quiet_enabled)
    s.setValue("notif/quiet_start", prefs.quiet_start_hour)
    s.setValue("notif/quiet_end", prefs.quiet_end_hour)
    s.setValue("notif/ch_telegram", prefs.channel_telegram)
    s.setValue("notif/ch_work_order", prefs.channel_work_order)
    s.setValue("notif/ch_system", prefs.channel_system)
    s.sync()


def is_quiet_hours(prefs: NotificationPrefs, *, now: datetime | None = None) -> bool:
    if not prefs.quiet_enabled:
        return False
    current = (now or datetime.now()).time()
    start = time(prefs.quiet_start_hour % 24, 0)
    end = time(prefs.quiet_end_hour % 24, 0)
    if start <= end:
        return start <= current < end
    # overnight window e.g. 22:00 → 07:00
    return current >= start or current < end


def channel_allowed(prefs: NotificationPrefs, kind: str) -> bool:
    if kind == "telegram":
        return prefs.channel_telegram
    if kind == "work_order":
        return prefs.channel_work_order
    if kind in {"system", "sync", "info"}:
        return prefs.channel_system
    return True
