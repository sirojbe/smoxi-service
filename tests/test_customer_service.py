"""Customer service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import ConflictError
from app.models.base import Base
from app.modules.customers.schemas.customer_schema import (
    CustomerCreateSchema,
    DeviceCreateSchema,
)
from app.modules.customers.services.customer_service import CustomerService
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


def test_create_customer_and_device(db_session: Session) -> None:
    service = CustomerService(db_session)
    customer = service.create_customer(
        1,
        CustomerCreateSchema(display_name="Ali Valiyev", phone="+998901112233"),
        actor_id=1,
    )
    device = service.create_device(
        customer.id,
        DeviceCreateSchema(model="iPhone 13", brand="Apple", imei="356938035643809"),
        actor_id=1,
    )
    db_session.commit()
    loaded = service.get_customer(customer.id)
    assert loaded.display_name == "Ali Valiyev"
    assert device.id is not None
    assert any(d.imei == "356938035643809" for d in loaded.devices if d.deleted_at is None)


def test_duplicate_phone_rejected(db_session: Session) -> None:
    service = CustomerService(db_session)
    service.create_customer(
        1,
        CustomerCreateSchema(display_name="Birinchi", phone="+998909998877"),
    )
    with pytest.raises(ConflictError):
        service.create_customer(
            1,
            CustomerCreateSchema(display_name="Ikkinchi", phone="+998909998877"),
        )
