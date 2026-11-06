"""Automation + AI assistant tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.ai_assistant.services.assistant_service import AiAssistantService
from app.modules.automation.models.rule import ACTION_NOTIFY, TRIGGER_MANUAL
from app.modules.automation.schemas.rule_schema import AutomationRuleCreateSchema
from app.modules.automation.services.automation_service import AutomationService
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


def test_seed_and_run_manual_rule(db_session: Session) -> None:
    svc = AutomationService(db_session)
    n = svc.seed_defaults(1, actor_id=1)
    assert n >= 1
    rule = svc.create_rule(
        1,
        AutomationRuleCreateSchema(
            name="Test qoʻlda",
            trigger_type=TRIGGER_MANUAL,
            action_type=ACTION_NOTIFY,
            action_payload="Test",
        ),
        actor_id=1,
    )
    run = svc.run_rule(rule.id, actor_id=1, context="pytest")
    db_session.commit()
    assert run.status == "ok"


def test_ai_suggestions_and_ask(db_session: Session) -> None:
    ai = AiAssistantService(db_session)
    tips = ai.suggestions(1)
    assert tips
    reply = ai.ask(1, "kam zaxira")
    assert "zaxira" in reply.text.lower() or "Kam" in reply.text
