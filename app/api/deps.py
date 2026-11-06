"""FastAPI dependencies — DB session and bearer auth."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.errors import http_error
from app.core.container import ServiceContainer
from app.core.exceptions import AuthenticationError
from app.modules.auth.services.auth_service import AuthService
from app.modules.users.models.user import User

_container: ServiceContainer | None = None


def bind_container(container: ServiceContainer) -> None:
    global _container
    _container = container


def get_container() -> ServiceContainer:
    if _container is None:
        raise RuntimeError("API container bogʻlanmagan.")
    return _container


def get_db() -> Generator[Session]:
    container = get_container()
    db = container.create_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise http_error(401, "unauthorized", "Bearer token majburiy.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise http_error(401, "unauthorized", "Bearer token boʻsh.")
    try:
        return AuthService(db).validate_session(token)
    except AuthenticationError as exc:
        raise http_error(401, "unauthorized", exc.message) from exc
