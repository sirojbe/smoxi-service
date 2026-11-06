"""In-app notification service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.notifications.services.notification_service import NotificationService
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


def test_telegram_inbound_creates_unread_notification(db_session: Session) -> None:
    service = NotificationService(db_session)
    service.notify_telegram_inbound(
        1,
        customer_name="Ali",
        chat_id="99",
        preview="Salom, qachon tayyor?",
        customer_id=None,
    )
    db_session.commit()
    assert service.count_unread(1) == 1
    rows = service.list_notifications(1, unread_only=True)
    assert len(rows) == 1
    assert rows[0].route == "telegram"
    assert rows[0].ref_key == "99"
    service.mark_all_read(1)
    db_session.commit()
    assert service.count_unread(1) == 0
