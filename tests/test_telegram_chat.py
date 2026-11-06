"""Telegram chat service persistence tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.telegram.services.chat_service import TelegramChatService
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


def test_inbound_message_creates_thread(db_session: Session) -> None:
    customer = CustomerService(db_session).create_customer(
        1,
        CustomerCreateSchema(display_name="Ali", phone="+998909998877"),
        actor_id=1,
    )
    customer.telegram_chat_id = "12345"
    db_session.flush()

    chat = TelegramChatService(db_session)
    chat.record_inbound(
        1,
        chat_id="12345",
        body="Salom, qachon tayyor?",
        customer_id=customer.id,
        telegram_message_id=99,
    )
    db_session.commit()

    threads = chat.list_threads(1)
    assert len(threads) == 1
    assert threads[0].chat_id == "12345"
    assert threads[0].unread_count == 1
    assert "Salom" in threads[0].last_body

    messages = chat.list_messages(1, "12345")
    assert len(messages) == 1
    assert messages[0].direction == "inbound"

    chat.mark_read(1, "12345")
    db_session.commit()
    threads = chat.list_threads(1)
    assert threads[0].unread_count == 0
