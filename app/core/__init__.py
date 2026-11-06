"""
SMOXI Service core domain primitives.

Shared enums, exceptions, and cross-cutting types used by all modules.
"""

from app.core.enums import SyncStatus, ThemeMode
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "NotFoundError",
    "SyncStatus",
    "ThemeMode",
    "ValidationError",
]
