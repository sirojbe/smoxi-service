"""Customer Telegram Mini App (CX Feature 13) — public repair portal."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.modules.customers.models.customer import Customer
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.cx.services.timeline_service import TimelineService
from app.modules.cx.services.warranty_service import WarrantyService
from app.modules.settings.services.settings_service import SettingsService
from app.modules.work_orders.models.status import WorkOrderStatus, status_label
from app.modules.work_orders.models.work_order import WorkOrder
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.schemas.work_order_schema import WorkOrderStatusChangeSchema
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.telegram.miniapp.auth import InitDataError, parse_and_validate_init_data

logger = get_logger("telegram.customer_miniapp")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DecisionBody(BaseModel):
    note: str | None = Field(default=None, max_length=500)


def create_customer_miniapp(
    container: ServiceContainer,
    *,
    company_id: int,
) -> FastAPI:
    """Customer-facing Mini App (separate auth from staff)."""
    app = FastAPI(title="SMOXI Customer Mini App", docs_url=None, redoc_url=None)

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

    def require_customer(
        db: Session = Depends(get_db),
        x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    ) -> Customer:
        company = SettingsService(db).get_company(company_id)
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            raise HTTPException(status_code=503, detail="Bot token sozlanmagan.")
        if not x_telegram_init_data:
            raise HTTPException(status_code=401, detail="Telegram initData yoʻq.")
        try:
            web_user = parse_and_validate_init_data(x_telegram_init_data, token)
        except InitDataError as exc:
            raise HTTPException(status_code=401, detail="Autentifikatsiya muvaffaqiyatsiz.") from exc
        customer = CustomerRepository(db).get_by_telegram_chat_id(
            company_id, str(web_user.id)
        )
        if customer is None:
            raise HTTPException(
                status_code=403,
                detail="Telegram akkauntingiz mijoz profiliga bogʻlanmagan. "
                "Botga /start yuboring yoki qabulxonaga murojaat qiling.",
            )
        return customer

    def _serialize_order(wo: WorkOrder) -> dict[str, Any]:
        return {
            "id": wo.id,
            "number": wo.number,
            "status": wo.status,
            "status_label": status_label(wo.status),
            "problem": (wo.problem_description or "")[:200],
            "estimated_cost": wo.estimated_cost or 0,
            "public_token": wo.public_token,
            "ready_at": wo.ready_at.isoformat() if wo.ready_at else None,
        }

    def _owned(db: Session, customer: Customer, work_order_id: int) -> WorkOrder:
        wo = WorkOrderRepository(db).get_by_id(work_order_id)
        if wo is None or wo.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
        if wo.customer_id != customer.id or wo.company_id != company_id:
            raise HTTPException(status_code=403, detail="Ruxsat yoʻq.")
        return wo

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "portal": "customer"}

    @app.get("/api/me")
    def me(customer: Customer = Depends(require_customer)) -> dict[str, Any]:
        return {
            "id": customer.id,
            "name": customer.display_name,
            "phone": customer.phone,
        }

    @app.get("/api/orders")
    def orders(
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        rows = WorkOrderRepository(db).list_for_customer(customer.id, limit=40)
        return [_serialize_order(wo) for wo in rows]

    @app.get("/api/orders/{work_order_id}")
    def order_detail(
        work_order_id: int,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        wo = _owned(db, customer, work_order_id)
        data = _serialize_order(wo)
        data["can_approve"] = (
            wo.status == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value
        )
        return data

    @app.get("/api/orders/{work_order_id}/timeline")
    def order_timeline(
        work_order_id: int,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        _owned(db, customer, work_order_id)
        events = TimelineService(db).list_events(work_order_id, customer_only=True)
        return [
            {
                "code": e.event_code,
                "title": e.title,
                "notes": e.notes,
                "at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

    @app.post("/api/orders/{work_order_id}/approve")
    def approve(
        work_order_id: int,
        body: DecisionBody,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        wo = _owned(db, customer, work_order_id)
        if wo.status != WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value:
            raise HTTPException(status_code=400, detail="Rozilik kutilmayapti.")
        try:
            updated = WorkOrderService(db).change_status(
                wo.id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.APPROVED.value,
                    note=body.note or "Mijoz Mini App orqali tasdiqladi",
                ),
                actor_id=None,
                notify=True,
                auto_advance=True,
            )
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return _serialize_order(updated)

    @app.post("/api/orders/{work_order_id}/reject")
    def reject(
        work_order_id: int,
        body: DecisionBody,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        wo = _owned(db, customer, work_order_id)
        if wo.status != WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value:
            raise HTTPException(status_code=400, detail="Rad etish mumkin emas.")
        note = (body.note or "").strip() or "Mijoz Mini App orqali rad etdi"
        try:
            updated = WorkOrderService(db).change_status(
                wo.id,
                WorkOrderStatusChangeSchema(
                    to_status=WorkOrderStatus.REJECTED.value,
                    note=note,
                ),
                actor_id=None,
                notify=False,
                auto_advance=False,
            )
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return _serialize_order(updated)

    @app.get("/api/orders/{work_order_id}/warranty")
    def warranty(
        work_order_id: int,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        _owned(db, customer, work_order_id)
        card = WarrantyService(db).get_for_work_order(work_order_id)
        if card is None:
            return {"warranty": None}
        return {
            "warranty": {
                "number": card.warranty_number,
                "issued_at": card.issued_at.isoformat(),
                "expires_at": card.expires_at.isoformat(),
                "period_days": card.period_days,
                "terms": card.terms,
            }
        }

    @app.get("/api/track/{public_token}")
    def track_by_token(
        public_token: str,
        customer: Customer = Depends(require_customer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        from sqlalchemy import select

        stmt = select(WorkOrder).where(
            WorkOrder.public_token == public_token,
            WorkOrder.company_id == company_id,
            WorkOrder.deleted_at.is_(None),
        )
        wo = db.scalar(stmt)
        if wo is None or wo.customer_id != customer.id:
            raise HTTPException(status_code=404, detail="QR buyurtma topilmadi.")
        return _serialize_order(wo)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app
