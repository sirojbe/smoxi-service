"""Warranty card issue (CX-G)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.time import utc_now
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.cx.models.cx_entities import WarrantyCard
from app.modules.cx.models.events import (
    EVENT_WARRANTY_STARTED,
    default_visibility_for_event,
    event_label,
)
from app.modules.cx.models.timeline_event import WorkOrderTimelineEvent
from app.modules.cx.services.wo_qr_service import generate_public_token
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService

DEFAULT_WARRANTY_DAYS = 30
DEFAULT_TERMS = "Kafolat faqat ushbu taʼmir doirasidagi ishlar uchun amal qiladi."


class WarrantyService:
    """Issue warranty cards when device is delivered."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._companies = CompanyRepository(session)
        self._customers = CustomerRepository(session)
        self._audit = AuditService(session)

    def get_for_work_order(self, work_order_id: int) -> WarrantyCard | None:
        stmt = select(WarrantyCard).where(
            WarrantyCard.work_order_id == work_order_id,
            WarrantyCard.deleted_at.is_(None),
        )
        return self._session.scalar(stmt)

    def issue_for_delivery(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
        period_days: int = DEFAULT_WARRANTY_DAYS,
    ) -> WarrantyCard:
        existing = self.get_for_work_order(work_order_id)
        if existing is not None:
            return existing
        work_order = self._work_orders.require_by_id(work_order_id)
        issued = utc_now()
        number = self._next_number(work_order.company_id)
        parts = ", ".join(p.name for p in (work_order.parts or [])[:20])
        card = WarrantyCard(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            warranty_number=number,
            public_token=generate_public_token(),
            period_days=period_days,
            issued_at=issued,
            expires_at=issued + timedelta(days=period_days),
            terms=DEFAULT_TERMS,
            parts_summary=parts or None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(card)
        self._session.flush()
        pdf_rel = self._write_pdf(card, work_order)
        card.pdf_path = pdf_rel
        code = EVENT_WARRANTY_STARTED
        self._session.add(
            WorkOrderTimelineEvent(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                event_code=code,
                visibility=default_visibility_for_event(code),
                title=event_label(code),
                notes=number,
                actor_id=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        self._audit.record(
            "cx_warranty_issued",
            actor_id=actor_id,
            entity_type="WarrantyCard",
            entity_id=card.id,
            entity_uuid=card.uuid,
            message=number,
        )
        return card

    def _next_number(self, company_id: int) -> str:
        stmt = select(func.count(WarrantyCard.id)).where(
            WarrantyCard.company_id == company_id,
            WarrantyCard.deleted_at.is_(None),
        )
        count = int(self._session.scalar(stmt) or 0) + 1
        return f"WR-{count:06d}"

    def _write_pdf(self, card: WarrantyCard, work_order: object) -> str | None:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            return None
        company = self._companies.get_by_id(card.company_id)
        customer = self._customers.get_by_id(work_order.customer_id)  # type: ignore[attr-defined]
        uploads = Path(get_settings().uploads_dir)
        out_dir = uploads / "cx" / f"c{card.company_id}" / f"wo{card.work_order_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{card.warranty_number}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        y = A4[1] - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Kafolat kartasi")
        y -= 24
        c.setFont("Helvetica", 11)
        c.drawString(40, y, f"Raqam: {card.warranty_number}")
        y -= 16
        c.drawString(40, y, f"WO: {work_order.number}")  # type: ignore[attr-defined]
        y -= 16
        if company:
            c.drawString(40, y, f"Kompaniya: {company.name}")
            y -= 16
        if customer:
            c.drawString(40, y, f"Mijoz: {customer.display_name}")
            y -= 16
        c.drawString(
            40,
            y,
            f"Muddat: {card.issued_at.date()} — {card.expires_at.date()} "
            f"({card.period_days} kun)",
        )
        y -= 16
        if card.parts_summary:
            c.drawString(40, y, f"Qismlar: {card.parts_summary[:80]}")
            y -= 16
        c.drawString(40, y, DEFAULT_TERMS)
        c.showPage()
        c.save()
        return str(path.relative_to(uploads)).replace("\\", "/")
