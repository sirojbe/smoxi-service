"""Staff Telegram Mini App FastAPI application."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.modules.inventory.schemas.item_schema import (
    InventoryItemCreateSchema,
    StockAdjustSchema,
)
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.reception.services.quick_intake_service import (
    QuickIntakeSchema,
    QuickIntakeService,
)
from app.modules.settings.services.settings_service import SettingsService
from app.modules.telegram.schemas import TelegramReplySchema
from app.modules.telegram.services.chat_service import TelegramChatService
from app.modules.users.models.user import User
from app.modules.users.repositories.user_repository import UserRepository
from app.modules.work_orders.models.status import WorkOrderStatus, status_label
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.telegram.miniapp.auth import InitDataError, parse_and_validate_init_data
from app.telegram.miniapp.session_token import (
    SessionTokenError,
    issue_staff_token,
    parse_staff_token,
)

logger = get_logger("telegram.miniapp")

STATIC_DIR = Path(__file__).resolve().parent / "static"

ACTIVE_READY_STATUSES = {
    WorkOrderStatus.WAITING_PARTS.value,
    WorkOrderStatus.REPAIRING.value,
    WorkOrderStatus.TESTING.value,
    WorkOrderStatus.QUALITY_CHECK.value,
}
PICKUP_STATUSES = {
    WorkOrderStatus.READY.value,
    WorkOrderStatus.REJECTED.value,
}


class ReplyBody(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1, max_length=4000)


class ReadyBody(BaseModel):
    number: str = Field(min_length=1, max_length=64)


class DeliverBody(BaseModel):
    number: str = Field(min_length=1, max_length=64)
    allow_unpaid: bool = False
    note: str | None = Field(default=None, max_length=500)


class IntakeBody(BaseModel):
    """Compact reception intake from Mini App."""

    phone: str = Field(min_length=5, max_length=32)
    display_name: str | None = Field(default=None, max_length=200)
    device_brand: str | None = Field(default=None, max_length=100)
    device_model: str = Field(min_length=1, max_length=150)
    problem_description: str = Field(min_length=3, max_length=4000)
    estimated_cost: int = Field(default=0, ge=0)
    accessories: str | None = Field(default=None, max_length=500)


class StockAdjustBody(BaseModel):
    movement_type: str = Field(default="adjust", max_length=16)
    quantity: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=255)


class StockItemCreateBody(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    quantity_on_hand: int = Field(default=0, ge=0)
    min_quantity: int = Field(default=0, ge=0)
    sale_price: int = Field(default=0, ge=0)
    unit: str = Field(default="dona", max_length=20)


class StaffLoginBody(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64)


class TelegramLoginBody(BaseModel):
    init_data: str = Field(min_length=10, max_length=4096)


def create_miniapp(
    container: ServiceContainer,
    *,
    company_id: int,
) -> FastAPI:
    """Build FastAPI app bound to one company and desktop container."""
    app = FastAPI(title="SMOXI Staff Mini App", docs_url=None, redoc_url=None)

    def get_db() -> Generator[Session]:
        db = container.create_session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _bot_secret(db: Session) -> str:
        from app.security.secrets import company_bot_token

        company = SettingsService(db).get_company(company_id)
        token = company_bot_token(company)
        if not token:
            raise HTTPException(status_code=503, detail="Bot token sozlanmagan.")
        return token

    def _issue_for_user(db: Session, user: User, telegram_id: str) -> dict[str, Any]:
        secret = _bot_secret(db)
        company = SettingsService(db).get_company(company_id)
        token = issue_staff_token(
            secret=secret,
            user_id=user.id,
            company_id=company_id,
            telegram_id=telegram_id,
        )
        return {
            "status": "ok",
            "token": token,
            "company": company.name,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
            },
        }

    def require_staff(
        db: Session = Depends(get_db),
        x_telegram_init_data: str | None = Header(
            default=None, alias="X-Telegram-Init-Data"
        ),
        authorization: str | None = Header(default=None),
    ) -> User:
        company = SettingsService(db).get_company(company_id)
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            raise HTTPException(status_code=503, detail="Bot token sozlanmagan.")

        bearer = ""
        if authorization and authorization.lower().startswith("bearer "):
            bearer = authorization[7:].strip()
        if bearer:
            try:
                session = parse_staff_token(bearer, secret=token, company_id=company_id)
            except SessionTokenError as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
            user = UserRepository(db).get_by_id(session.user_id)
            if user is None or user.company_id != company_id or not user.is_active:
                raise HTTPException(status_code=401, detail="Sessiya yaroqsiz.")
            return user

        if x_telegram_init_data:
            try:
                web_user = parse_and_validate_init_data(x_telegram_init_data, token)
            except InitDataError as exc:
                logger.warning("Mini App auth xato: {}", exc)
                raise HTTPException(
                    status_code=401, detail="Autentifikatsiya muvaffaqiyatsiz."
                ) from exc
            staff = SettingsService(db).resolve_staff_user(company_id, web_user.id)
            if staff is None:
                raise HTTPException(
                    status_code=403, detail="Bu Telegram ID ruxsat etilmagan."
                )
            return staff

        raise HTTPException(
            status_code=401,
            detail="Kirish talab qilinadi. Telegram orqali oching yoki ID kiriting.",
        )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/telegram")
    def auth_telegram(
        payload: TelegramLoginBody,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        secret = _bot_secret(db)
        try:
            web_user = parse_and_validate_init_data(payload.init_data, secret)
        except InitDataError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        staff = SettingsService(db).resolve_staff_user(company_id, web_user.id)
        if staff is None:
            raise HTTPException(
                status_code=403, detail="Bu Telegram ID ruxsat etilmagan."
            )
        return _issue_for_user(db, staff, web_user.id)

    @app.post("/api/auth/staff")
    def auth_staff(
        payload: StaffLoginBody,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        try:
            user = SettingsService(db).authenticate_staff_chat(
                company_id,
                chat_id=payload.chat_id,
            )
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return _issue_for_user(db, user, payload.chat_id.strip())

    @app.get("/api/me")
    def me(
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        company = SettingsService(db).get_company(company_id)
        return {
            "company": company.name,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
            },
            "mini_app_url": company.telegram_mini_app_url,
        }

    @app.get("/api/unread")
    def unread(
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        _ = user
        chat = TelegramChatService(db)
        notif = NotificationService(db)
        threads = [t for t in chat.list_threads(company_id) if t.unread_count > 0]
        return {
            "unread_messages": chat.count_unread(company_id),
            "unread_notifications": notif.count_unread(company_id),
            "threads": [
                {
                    "chat_id": t.chat_id,
                    "customer_name": t.customer_name,
                    "last_body": t.last_body,
                    "unread_count": t.unread_count,
                }
                for t in threads[:30]
            ],
        }

    @app.get("/api/orders")
    def orders(
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
        ready_only: bool = False,
        pickup_only: bool = False,
    ) -> dict[str, Any]:
        _ = user
        rows = WorkOrderRepository(db).search(company_id, limit=40)
        if pickup_only:
            rows = [o for o in rows if o.status in PICKUP_STATUSES]
        elif ready_only:
            rows = [o for o in rows if o.status in ACTIVE_READY_STATUSES]
        service = WorkOrderService(db)
        payload_rows: list[dict[str, Any]] = []
        for o in rows[:30]:
            unpaid = 0
            if o.status in PICKUP_STATUSES:
                try:
                    unpaid = service.unpaid_balance_for_work_order(o.id)
                except Exception:  # noqa: BLE001
                    unpaid = 0
            payload_rows.append(
                {
                    "id": o.id,
                    "number": o.number,
                    "status": o.status,
                    "status_label": status_label(o.status),
                    "problem": (o.problem_description or "")[:120],
                    "unpaid_balance": unpaid,
                }
            )
        return {"orders": payload_rows}

    @app.get("/api/threads")
    def threads(
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        _ = user
        chat = TelegramChatService(db)
        items = chat.list_threads(company_id)
        return {
            "threads": [
                {
                    "chat_id": t.chat_id,
                    "customer_name": t.customer_name,
                    "last_body": t.last_body,
                    "unread_count": t.unread_count,
                }
                for t in items[:40]
            ]
        }

    @app.post("/api/reply")
    def reply(
        payload: ReplyBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, str]:
        try:
            TelegramChatService(db).reply(
                company_id,
                TelegramReplySchema(chat_id=payload.chat_id, body=payload.body),
                actor_id=user.id,
            )
            NotificationService(db).mark_all_read(company_id)
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {"status": "ok"}

    @app.post("/api/ready")
    def ready(
        payload: ReadyBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        number = payload.number.strip().upper()
        found = WorkOrderRepository(db).search(company_id, query=number, limit=5)
        order = next((o for o in found if o.number.upper() == number), None)
        if order is None:
            raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
        try:
            result = WorkOrderService(db).mark_ready(order.id, actor_id=user.id)
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {
            "status": "ok",
            "number": result.work_order.number,
            "telegram": result.telegram_reason,
        }

    @app.post("/api/deliver")
    def deliver(
        payload: DeliverBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        number = payload.number.strip().upper()
        found = WorkOrderRepository(db).search(company_id, query=number, limit=5)
        order = next((o for o in found if o.number.upper() == number), None)
        if order is None:
            raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
        try:
            result = WorkOrderService(db).mark_delivered(
                order.id,
                actor_id=user.id,
                allow_unpaid=payload.allow_unpaid,
                note=payload.note,
            )
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {
            "status": "ok",
            "number": result.work_order.number,
            "telegram": result.telegram_reason,
            "unpaid_balance": result.unpaid_balance,
        }

    @app.post("/api/intake")
    def intake(
        payload: IntakeBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        try:
            schema = QuickIntakeSchema(
                phone=payload.phone,
                display_name=payload.display_name,
                device_brand=payload.device_brand,
                device_model=payload.device_model,
                problem_description=payload.problem_description,
                estimated_cost=payload.estimated_cost,
                accessories=payload.accessories,
            )
            result = QuickIntakeService(db).intake(
                company_id,
                schema,
                actor_id=user.id,
            )
        except PydanticValidationError as exc:
            msg = str(exc.errors()[0].get("msg") if exc.errors() else exc)
            raise HTTPException(status_code=400, detail=msg) from exc
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {
            "status": "ok",
            "number": result.work_order.number,
            "work_order_id": result.work_order.id,
            "customer": result.customer.display_name,
            "created_customer": result.created_customer,
            "telegram_sent": result.telegram_sent,
            "bot_link": result.bot_link,
        }

    @app.get("/api/inventory")
    def inventory_list(
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
        q: str | None = None,
        low_stock_only: bool = False,
    ) -> dict[str, Any]:
        _ = user
        items = InventoryService(db).list_items(
            company_id, query=q, low_stock_only=low_stock_only
        )
        return {
            "items": [
                {
                    "id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "unit": item.unit,
                    "quantity_on_hand": item.quantity_on_hand,
                    "min_quantity": item.min_quantity,
                    "sale_price": item.sale_price,
                    "low_stock": item.quantity_on_hand <= item.min_quantity,
                }
                for item in items[:80]
            ]
        }

    @app.post("/api/inventory")
    def inventory_create(
        payload: StockItemCreateBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        try:
            item = InventoryService(db).create_item(
                company_id,
                InventoryItemCreateSchema(
                    sku=payload.sku,
                    name=payload.name,
                    quantity_on_hand=payload.quantity_on_hand,
                    min_quantity=payload.min_quantity,
                    sale_price=payload.sale_price,
                    unit=payload.unit,
                ),
                actor_id=user.id,
            )
        except PydanticValidationError as exc:
            msg = str(exc.errors()[0].get("msg") if exc.errors() else exc)
            raise HTTPException(status_code=400, detail=msg) from exc
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {
            "status": "ok",
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "quantity_on_hand": item.quantity_on_hand,
        }

    @app.post("/api/inventory/{item_id}/adjust")
    def inventory_adjust(
        item_id: int,
        payload: StockAdjustBody,
        user: User = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        try:
            item = InventoryService(db).adjust_stock(
                item_id,
                StockAdjustSchema(
                    movement_type=payload.movement_type,
                    quantity=payload.quantity,
                    reason=payload.reason or "Mini App orqali",
                ),
                actor_id=user.id,
            )
        except PydanticValidationError as exc:
            msg = str(exc.errors()[0].get("msg") if exc.errors() else exc)
            raise HTTPException(status_code=400, detail=msg) from exc
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return {
            "status": "ok",
            "id": item.id,
            "sku": item.sku,
            "quantity_on_hand": item.quantity_on_hand,
        }

    # Customer portal (Feature 13) — separate auth, same HTTPS tunnel
    from app.telegram.customer_miniapp.app import create_customer_miniapp

    customer_app = create_customer_miniapp(container, company_id=company_id)
    app.mount("/customer", customer_app)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        path = request.url.path
        if path.endswith((".js", ".css", ".html")):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    return app
