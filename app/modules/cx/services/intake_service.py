"""Intake snapshot, signature, and receipt PDF (CX-B)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.exceptions import ValidationError
from app.core.time import utc_now
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.cx.models.cx_entities import (
    CustomerSignature,
    IntakeSnapshot,
    ReceiptDocument,
)
from app.modules.cx.services.media_store import MediaStore
from app.modules.cx.services.wo_qr_service import WorkOrderQrService
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService

DEFAULT_TERMS = (
    "Men qurilmani tekshirib topshirdim. Holat va aksessuarlar toʻgʻri "
    "koʻrsatilganiga roziman. Taʼmir shartlariga roziman."
)
TERMS_VERSION = "1.0"


class IntakeService:
    """Save reception snapshot and capture signature / PDF."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._companies = CompanyRepository(session)
        self._customers = CustomerRepository(session)
        self._audit = AuditService(session)
        self._qr = WorkOrderQrService(session)

    def get_snapshot(self, work_order_id: int) -> IntakeSnapshot | None:
        stmt = select(IntakeSnapshot).where(
            IntakeSnapshot.work_order_id == work_order_id,
            IntakeSnapshot.deleted_at.is_(None),
        )
        return self._session.scalar(stmt)

    def save_snapshot(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
        customer_email: str | None = None,
        device_category: str | None = None,
        serial_number: str | None = None,
        imei: str | None = None,
        color: str | None = None,
        capacity: str | None = None,
        accessories: str | None = None,
        has_sim: bool = False,
        has_memory_card: bool = False,
        battery_status: str | None = None,
        screen_condition: str | None = None,
        body_condition: str | None = None,
        water_damage: bool = False,
        previous_repairs: str | None = None,
        internal_notes: str | None = None,
        estimated_completion: datetime | None = None,
    ) -> IntakeSnapshot:
        work_order = self._work_orders.require_by_id(work_order_id)
        snap = self.get_snapshot(work_order_id)
        if snap is None:
            snap = IntakeSnapshot(
                company_id=work_order.company_id,
                work_order_id=work_order.id,
                created_by=actor_id,
            )
            self._session.add(snap)
        snap.customer_email = customer_email
        snap.device_category = device_category
        snap.serial_number = serial_number
        snap.imei = imei
        snap.color = color
        snap.capacity = capacity
        snap.accessories = accessories
        snap.has_sim = has_sim
        snap.has_memory_card = has_memory_card
        snap.battery_status = battery_status
        snap.screen_condition = screen_condition
        snap.body_condition = body_condition
        snap.water_damage = water_damage
        snap.previous_repairs = previous_repairs
        snap.internal_notes = internal_notes
        snap.estimated_completion = estimated_completion
        snap.updated_by = actor_id
        self._session.flush()
        return snap

    def get_signature(self, work_order_id: int) -> CustomerSignature | None:
        stmt = (
            select(CustomerSignature)
            .where(
                CustomerSignature.work_order_id == work_order_id,
                CustomerSignature.deleted_at.is_(None),
            )
            .order_by(CustomerSignature.id.desc())
        )
        return self._session.scalar(stmt)

    def capture_signature(
        self,
        work_order_id: int,
        png_bytes: bytes,
        *,
        actor_id: int | None = None,
        terms: str = DEFAULT_TERMS,
    ) -> CustomerSignature:
        if self.get_signature(work_order_id) is not None:
            raise ValidationError("Imzo allaqachon tasdiqlangan va oʻzgartirilmaydi.")
        if not png_bytes:
            raise ValidationError("Imzo boʻsh.")
        work_order = self._work_orders.require_by_id(work_order_id)
        store = MediaStore(company_id=work_order.company_id, work_order_id=work_order.id)
        tmp = store.root / "_sig_tmp.png"
        tmp.write_bytes(png_bytes)
        rel, _size, _ = store.save_file(tmp, prefix="signature")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        terms_hash = hashlib.sha256(terms.encode("utf-8")).hexdigest()
        sig = CustomerSignature(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            signature_path=rel,
            terms_version=TERMS_VERSION,
            terms_hash=terms_hash,
            signed_at=utc_now(),
            employee_id=actor_id,
            is_locked=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(sig)
        self._session.flush()
        self._audit.record(
            "cx_signature_captured",
            actor_id=actor_id,
            entity_type="CustomerSignature",
            entity_id=sig.id,
            entity_uuid=sig.uuid,
            message=work_order.number,
        )
        return sig

    def generate_receipt_pdf(
        self,
        work_order_id: int,
        *,
        actor_id: int | None = None,
    ) -> ReceiptDocument:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise ValidationError("PDF uchun reportlab o‘rnatilmagan.") from exc

        work_order = self._work_orders.require_by_id(work_order_id)
        company = self._companies.get_by_id(work_order.company_id)
        customer = self._customers.get_by_id(work_order.customer_id)
        snap = self.get_snapshot(work_order_id)
        sig = self.get_signature(work_order_id)
        self._qr.ensure_public_token(work_order, actor_id=actor_id)

        uploads = Path(get_settings().uploads_dir)
        out_dir = uploads / "cx" / f"c{work_order.company_id}" / f"wo{work_order.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        version = self._next_receipt_version(work_order_id)
        filename = f"receipt_v{version}.pdf"
        abs_path = out_dir / filename

        c = canvas.Canvas(str(abs_path), pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, (company.name if company else "SMOXI Service"))
        y -= 22
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Qabul dalolatnomasi — {work_order.number}")
        y -= 18
        if customer:
            c.drawString(40, y, f"Mijoz: {customer.display_name}  Tel: {customer.phone}")
            y -= 14
        if snap:
            c.drawString(
                40,
                y,
                f"IMEI: {snap.imei or '—'}  SN: {snap.serial_number or '—'}",
            )
            y -= 14
            c.drawString(
                40,
                y,
                f"Ekran: {snap.screen_condition or '—'}  "
                f"Korpus: {snap.body_condition or '—'}",
            )
            y -= 14
        c.drawString(40, y, f"Muammo: {(work_order.problem_description or '')[:90]}")
        y -= 20
        c.drawString(40, y, DEFAULT_TERMS[:95])
        y -= 14
        c.drawString(40, y, DEFAULT_TERMS[95:190] if len(DEFAULT_TERMS) > 95 else "")
        y -= 30
        if sig:
            sig_abs = uploads / sig.signature_path
            if sig_abs.is_file():
                try:
                    c.drawImage(
                        str(sig_abs),
                        40,
                        y - 60,
                        width=180,
                        height=60,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:  # noqa: BLE001
                    c.drawString(40, y, "[Imzo fayli]")
            c.drawString(40, y - 75, f"Imzo: {sig.signed_at}")
        c.showPage()
        c.save()

        rel = str(abs_path.relative_to(uploads)).replace("\\", "/")
        doc = ReceiptDocument(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            doc_version=version,
            file_path=rel,
            generated_at=utc_now(),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(doc)
        self._session.flush()
        self._audit.record(
            "cx_receipt_generated",
            actor_id=actor_id,
            entity_type="ReceiptDocument",
            entity_id=doc.id,
            entity_uuid=doc.uuid,
            message=rel,
        )
        return doc

    def _next_receipt_version(self, work_order_id: int) -> int:
        stmt = select(ReceiptDocument).where(
            ReceiptDocument.work_order_id == work_order_id,
            ReceiptDocument.deleted_at.is_(None),
        )
        rows = list(self._session.scalars(stmt))
        if not rows:
            return 1
        return max(r.doc_version for r in rows) + 1
