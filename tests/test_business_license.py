"""Business client and license tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.modules.business_clients.schemas.business_client_schema import (
    BusinessClientCreateSchema,
    ContactCreateSchema,
)
from app.modules.business_clients.services.business_client_service import BusinessClientService
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.license.services.license_service import LicenseService
from app.modules.settings.services.settings_service import SettingsService
from app.services.bootstrap_service import BootstrapService
from app.ui.shell.sidebar import Sidebar


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


def test_business_client_contact_and_link(db_session: Session) -> None:
    bc = BusinessClientService(db_session)
    client = bc.create_client(
        1,
        BusinessClientCreateSchema(
            name="Acme LLC",
            tax_id="123",
            credit_limit=Decimal("1000000"),
        ),
        actor_id=1,
    )
    bc.add_contact(
        client.id,
        ContactCreateSchema(full_name="Ali", phone="+998901112233"),
        actor_id=1,
    )
    customer = CustomerService(db_session).create_customer(
        1,
        CustomerCreateSchema(display_name="Ali Valiyev", phone="+998909998877"),
        actor_id=1,
    )
    bc.link_customer(client.id, customer.id, actor_id=1)
    db_session.commit()
    linked = bc.list_linked_customers(client.id)
    assert len(linked) == 1
    assert linked[0].business_client_id == client.id


def test_license_activate_and_user_seat(db_session: Session) -> None:
    lic = LicenseService(db_session)
    status = lic.get_status(1)
    assert status.is_valid
    lic.activate(1, "SMOXI-STD-TESTKEY", actor_id=1)
    db_session.commit()
    status2 = lic.get_status(1)
    assert status2.plan_code == "standard"
    assert status2.seats == 10

    settings = SettingsService(db_session)
    roles = settings.list_roles()
    reception = next(r for r in roles if r.code == "reception")
    user = settings.create_user(
        1,
        username="reception1",
        password="1234",
        full_name="Qabul",
        role_id=reception.id,
        actor_id=1,
    )
    db_session.commit()
    assert user.id is not None


def test_sidebar_has_companies() -> None:
    assert "companies" in [r[0] for r in Sidebar.ROUTES]
