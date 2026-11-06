"""Password hashing utilities."""

from __future__ import annotations

import secrets

from passlib.context import CryptContext

_PASSWORD_CONTEXT = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """Return a secure hash for *plain_password*."""
    return _PASSWORD_CONTEXT.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify *plain_password* against *password_hash*."""
    return _PASSWORD_CONTEXT.verify(plain_password, password_hash)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(48)
