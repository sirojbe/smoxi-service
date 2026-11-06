"""Sync module."""

__all__ = ["SyncService"]


def __getattr__(name: str):
    if name == "SyncService":
        from app.modules.sync.services.sync_service import SyncService

        return SyncService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
