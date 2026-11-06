"""Calendar module tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.exceptions import ValidationError
from app.models.base import Base
from app.modules.calendar.models.event import EVENT_APPOINTMENT
from app.modules.calendar.schemas.event_schema import CalendarEventCreateSchema
from app.modules.calendar.services.calendar_service import CalendarService
from app.services.bootstrap_service import BootstrapService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    BootstrapService(session).ensure_system_data()
    session.commit()
    yield session
    session.close()


def test_create_and_list_calendar_event(db_session: Session) -> None:
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(hours=1)
    service = CalendarService(db_session)
    event = service.create_event(
        1,
        CalendarEventCreateSchema(
            title="Mijoz uchrashuvi",
            event_type=EVENT_APPOINTMENT,
            starts_at=start,
            ends_at=end,
            location="Qabulxona",
        ),
        actor_id=1,
    )
    db_session.commit()
    assert event.id
    rows = service.list_range(
        1,
        range_start=start - timedelta(minutes=5),
        range_end=end + timedelta(minutes=5),
    )
    assert any(r.id == event.id for r in rows)


def test_invalid_time_range(db_session: Session) -> None:
    start = datetime.now(UTC)
    with pytest.raises(ValidationError):
        CalendarService(db_session).create_event(
            1,
            CalendarEventCreateSchema(
                title="Xato",
                starts_at=start,
                ends_at=start,
            ),
            actor_id=1,
        )
