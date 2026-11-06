"""Authentication service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.auth.services.auth_service import AuthService
from app.services.bootstrap_service import BootstrapService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    BootstrapService(session).ensure_system_data()
    session.commit()
    yield session
    session.close()


def test_login_success(db_session: Session) -> None:
    auth = AuthService(db_session)
    result = auth.login(company_code="smoxi", username="1", password="1234")
    assert result.user.username == "1"
    assert result.session_token


def test_login_invalid_password(db_session: Session) -> None:
    from app.core.exceptions import AuthenticationError

    auth = AuthService(db_session)
    with pytest.raises(AuthenticationError):
        auth.login(company_code="smoxi", username="1", password="bad-password")


def test_change_password_min_four_chars(db_session: Session) -> None:
    auth = AuthService(db_session)
    result = auth.login(company_code="smoxi", username="1", password="1234")
    assert result.user.must_change_password is True
    updated = auth.change_password(
        result.user.id,
        current_password="1234",
        new_password="5678",
    )
    assert updated.must_change_password is False
    again = auth.login(company_code="smoxi", username="1", password="5678")
    assert again.user.username == "1"


def test_change_password_rejects_default_and_short(db_session: Session) -> None:
    from app.core.exceptions import ValidationError

    auth = AuthService(db_session)
    result = auth.login(company_code="smoxi", username="1", password="1234")
    with pytest.raises(ValidationError):
        auth.change_password(
            result.user.id,
            current_password="1234",
            new_password="123",
        )
    with pytest.raises(ValidationError):
        auth.change_password(
            result.user.id,
            current_password="1234",
            new_password="1234",
        )
