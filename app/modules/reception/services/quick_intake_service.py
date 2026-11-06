"""Quick reception intake — phone first, parts, auto expense."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config.constants import DEFAULT_SERVICE_PRICE
from app.core.exceptions import ConflictError, ValidationError
from app.core.phone import (
    bot_deep_link,
    normalize_phone,
    start_payload_for_phone,
    start_payload_for_work_order,
)
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.models.customer import Customer
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.customers.schemas.customer_schema import CustomerCreateSchema, DeviceCreateSchema
from app.modules.customers.services.customer_service import CustomerService
from app.modules.work_orders.models.status import WorkOrderPriority, WorkOrderStatus
from app.modules.work_orders.models.work_order import WorkOrder
from app.modules.work_orders.schemas.work_order_schema import (
    WorkOrderCreateSchema,
    WorkOrderPartSchema,
    WorkOrderStatusChangeSchema,
)
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.services.audit_service import AuditService
from app.telegram.notifier import TelegramNotifier


class QuickIntakeSchema(BaseModel):
    """Walk-in intake payload."""

    phone: str = Field(min_length=5, max_length=32)
    display_name: str | None = Field(default=None, max_length=200)
    device_model: str = Field(min_length=1, max_length=150)
    device_brand: str | None = Field(default=None, max_length=100)
    problem_description: str = Field(min_length=3, max_length=4000)
    work_scope: str | None = None
    estimated_cost: int = Field(ge=0, default=DEFAULT_SERVICE_PRICE)
    telegram_chat_id: str | None = Field(default=None, max_length=64)
    accessories: str | None = None
    # CX intake
    customer_email: str | None = Field(default=None, max_length=255)
    device_category: str | None = Field(default=None, max_length=64)
    serial_number: str | None = Field(default=None, max_length=128)
    imei: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=64)
    capacity: str | None = Field(default=None, max_length=64)
    has_sim: bool = False
    has_memory_card: bool = False
    battery_status: str | None = Field(default=None, max_length=64)
    screen_condition: str | None = Field(default=None, max_length=64)
    body_condition: str | None = Field(default=None, max_length=64)
    water_damage: bool = False
    previous_repairs: str | None = None
    internal_notes: str | None = None
    priority: str = WorkOrderPriority.NORMAL.value
    parts: list[WorkOrderPartSchema] = Field(default_factory=list)

    @field_validator("phone", "device_model", "problem_description")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Maydon boʻsh boʻlishi mumkin emas.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def normalize(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator(
        "display_name",
        "device_brand",
        "telegram_chat_id",
        "accessories",
        "work_scope",
        "customer_email",
        "device_category",
        "serial_number",
        "imei",
        "color",
        "capacity",
        "battery_status",
        "screen_condition",
        "body_condition",
        "previous_repairs",
        "internal_notes",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return WorkOrderPriority(value).value


class QuickIntakeResult:
    """Result of quick intake."""

    def __init__(
        self,
        *,
        customer: Customer,
        work_order: WorkOrder,
        telegram_sent: bool,
        created_customer: bool,
        bot_link: str | None = None,
        expense_total: int = 0,
        customer_total: int = 0,
    ) -> None:
        self.customer = customer
        self.work_order = work_order
        self.telegram_sent = telegram_sent
        self.created_customer = created_customer
        self.bot_link = bot_link
        self.expense_total = expense_total
        self.customer_total = customer_total


class QuickIntakeService:
    """Phone → WO + parts expense → Telegram by linked phone."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._customer_service = CustomerService(session)
        self._work_orders = WorkOrderService(session)
        self._companies = CompanyRepository(session)
        self._notifier = TelegramNotifier(session)
        self._audit = AuditService(session)

    def intake(
        self,
        company_id: int,
        payload: QuickIntakeSchema,
        *,
        actor_id: int | None = None,
        branch_id: int | None = None,
    ) -> QuickIntakeResult:
        company = self._companies.get_by_id(company_id)
        if company is None:
            raise ValidationError("Kompaniya topilmadi.")

        phone = normalize_phone(payload.phone)
        created_customer = False
        # Soft-deleted mijozlar ham unique phone egasi — qayta ochib ishlatamiz.
        customer = self._customers.get_by_phone(company_id, phone, include_deleted=True)
        if customer is None:
            name = payload.display_name or f"Mijoz {phone}"
            try:
                customer = self._customer_service.create_customer(
                    company_id,
                    CustomerCreateSchema(display_name=name, phone=phone),
                    actor_id=actor_id,
                )
                created_customer = True
            except ConflictError:
                # Parallel create / format farqi — qayta qidiramiz.
                customer = self._customers.get_by_phone(
                    company_id, phone, include_deleted=True
                )
                if customer is None:
                    raise
        if customer.deleted_at is not None:
            customer.restore(actor_id=actor_id)
            self._customers.save(customer)
        if not created_customer:
            if customer.phone != phone:
                customer.phone = phone
            if payload.display_name and customer.display_name != payload.display_name:
                customer.display_name = payload.display_name
            customer.updated_by = actor_id
            self._customers.save(customer)
        elif payload.display_name and customer.display_name != payload.display_name:
            customer.display_name = payload.display_name
            customer.updated_by = actor_id
            self._customers.save(customer)

        if payload.telegram_chat_id:
            customer.telegram_chat_id = payload.telegram_chat_id
            customer.updated_by = actor_id
            self._customers.save(customer)

        if payload.customer_email:
            customer.email = payload.customer_email
            customer.updated_by = actor_id
            self._customers.save(customer)

        device = self._customer_service.create_device(
            customer.id,
            DeviceCreateSchema(
                device_type=payload.device_category or "phone",
                brand=payload.device_brand,
                model=payload.device_model,
                serial_number=payload.serial_number,
                imei=payload.imei,
                color=payload.color,
            ),
            actor_id=actor_id,
        )

        service_price = (
            payload.estimated_cost
            if payload.estimated_cost > 0
            else DEFAULT_SERVICE_PRICE
        )
        work_order = self._work_orders.create_from_reception(
            company_id,
            WorkOrderCreateSchema(
                customer_id=customer.id,
                device_id=device.id,
                branch_id=branch_id,
                problem_description=payload.problem_description,
                work_scope=payload.work_scope,
                accessories=payload.accessories,
                notes=payload.internal_notes,
                priority=payload.priority,
                estimated_cost=service_price,
                parts=payload.parts,
            ),
            actor_id=actor_id,
        )

        from app.modules.cx.services.intake_service import IntakeService

        IntakeService(self._session).save_snapshot(
            work_order.id,
            actor_id=actor_id,
            customer_email=payload.customer_email,
            device_category=payload.device_category or "phone",
            serial_number=payload.serial_number,
            imei=payload.imei,
            color=payload.color,
            capacity=payload.capacity,
            accessories=payload.accessories,
            has_sim=payload.has_sim,
            has_memory_card=payload.has_memory_card,
            battery_status=payload.battery_status,
            screen_condition=payload.screen_condition,
            body_condition=payload.body_condition,
            water_damage=payload.water_damage,
            previous_repairs=payload.previous_repairs,
            internal_notes=payload.internal_notes,
        )

        telegram_sent = False
        if (work_order.estimated_cost or 0) > 0:
            self._work_orders.change_status(
                work_order.id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.DIAGNOSING.value,
                    note="Tezkor qabul — diagnostika",
                ),
                actor_id=actor_id,
                notify=False,
            )
            work_order = self._work_orders.change_status(
                work_order.id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value,
                    note="Narx tasdiqi kutilmoqda",
                ),
                actor_id=actor_id,
                notify=False,
            )
            telegram_sent = self._notifier.notify_quote(work_order, customer, company)
        else:
            telegram_sent = self._notifier.notify_received(work_order, customer, company)

        bot_link = bot_deep_link(
            company.telegram_bot_username,
            start_payload_for_work_order(work_order.id)
            if work_order.id
            else start_payload_for_phone(phone),
        )

        self._audit.record(
            "quick_intake_completed",
            actor_id=actor_id,
            entity_type="WorkOrder",
            entity_id=work_order.id,
            entity_uuid=work_order.uuid,
            message=work_order.number,
        )
        return QuickIntakeResult(
            customer=customer,
            work_order=work_order,
            telegram_sent=telegram_sent,
            created_customer=created_customer,
            bot_link=bot_link,
            expense_total=work_order.expense_total,
            customer_total=work_order.estimated_cost or 0,
        )
