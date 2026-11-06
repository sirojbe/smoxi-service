"""Notification preference helpers tests."""

from __future__ import annotations

from datetime import datetime

from app.modules.notifications.services.prefs import (
    NotificationPrefs,
    channel_allowed,
    is_quiet_hours,
)


def test_quiet_hours_overnight() -> None:
    prefs = NotificationPrefs(quiet_enabled=True, quiet_start_hour=22, quiet_end_hour=7)
    assert is_quiet_hours(prefs, now=datetime(2026, 7, 24, 23, 0))
    assert is_quiet_hours(prefs, now=datetime(2026, 7, 24, 3, 0))
    assert not is_quiet_hours(prefs, now=datetime(2026, 7, 24, 10, 0))


def test_channel_allowed() -> None:
    prefs = NotificationPrefs(channel_telegram=False, channel_work_order=True)
    assert not channel_allowed(prefs, "telegram")
    assert channel_allowed(prefs, "work_order")
