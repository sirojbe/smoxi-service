"""Core enumerations shared across SMOXI Service."""

from __future__ import annotations

from enum import StrEnum


class SyncStatus(StrEnum):
    """Cloud synchronization state for offline-first entities."""

    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


class ThemeMode(StrEnum):
    """Application visual theme preference."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
