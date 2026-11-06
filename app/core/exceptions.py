"""Application-wide exception hierarchy."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for recoverable application errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "SMOXI-APP-000"


class ValidationError(AppError):
    """Raised when input or business validation fails."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message, code="SMOXI-VAL-001")
        self.field = field


class NotFoundError(AppError):
    """Raised when a requested entity does not exist."""

    def __init__(self, message: str, *, entity: str | None = None) -> None:
        super().__init__(message, code="SMOXI-NF-001")
        self.entity = entity


class ConflictError(AppError):
    """Raised on version conflicts or duplicate unique values."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="SMOXI-CNF-001")


class AuthenticationError(AppError):
    """Raised when credentials or session are invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="SMOXI-AUTH-001")


class AuthorizationError(AppError):
    """Raised when the user lacks permission for an action."""

    def __init__(self, message: str, *, permission: str | None = None) -> None:
        super().__init__(message, code="SMOXI-AUTHZ-001")
        self.permission = permission
