"""API package — FastAPI /api/v1 surface.

Import ``create_api_app`` from ``app.api.app`` (not this package root) to avoid
circular imports with SyncService ↔ API schemas.
"""

__all__ = ["create_api_app"]


def __getattr__(name: str):
    if name == "create_api_app":
        from app.api.app import create_api_app

        return create_api_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
