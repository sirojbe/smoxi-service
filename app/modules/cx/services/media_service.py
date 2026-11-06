"""CX media application service."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.modules.cx.models.cx_entities import MediaAsset
from app.modules.cx.models.events import EVENT_NOTE_ADDED, VISIBILITY_STAFF
from app.modules.cx.models.timeline_event import WorkOrderTimelineEvent
from app.modules.cx.services.media_store import MediaStore
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.services.audit_service import AuditService

PHOTO_CATEGORIES = {
    "front",
    "back",
    "left",
    "right",
    "top",
    "bottom",
    "screen",
    "camera",
    "ports",
    "damage",
    "accessories",
    "other",
}


class MediaService:
    """Upload / list / soft-hide work order media."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._work_orders = WorkOrderRepository(session)
        self._audit = AuditService(session)

    def list_media(
        self,
        work_order_id: int,
        *,
        include_hidden: bool = False,
    ) -> list[MediaAsset]:
        stmt = select(MediaAsset).where(
            MediaAsset.work_order_id == work_order_id,
            MediaAsset.deleted_at.is_(None),
        )
        if not include_hidden:
            stmt = stmt.where(MediaAsset.is_hidden.is_(False))
        stmt = stmt.order_by(MediaAsset.captured_at.desc(), MediaAsset.id.desc())
        return list(self._session.scalars(stmt))

    def add_photo(
        self,
        work_order_id: int,
        source_path: Path,
        *,
        category: str = "other",
        phase: str = "before",
        actor_id: int | None = None,
        customer_visible: bool = True,
    ) -> MediaAsset:
        work_order = self._work_orders.require_by_id(work_order_id)
        cat = category if category in PHOTO_CATEGORIES else "other"
        store = MediaStore(company_id=work_order.company_id, work_order_id=work_order.id)
        rel, size, checksum = store.save_file(source_path, prefix=f"photo_{cat}")
        asset = MediaAsset(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            media_type="photo",
            category=cat,
            phase=phase if phase in {"before", "after"} else "before",
            file_path=rel,
            original_name=source_path.name,
            mime_type=None,
            file_size=size,
            checksum=checksum,
            captured_at=utc_now(),
            customer_visible=customer_visible,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(asset)
        self._session.flush()
        self._timeline_note(
            work_order.company_id,
            work_order.id,
            f"Foto qoʻshildi ({cat})",
            actor_id,
        )
        self._audit.record(
            "cx_media_added",
            actor_id=actor_id,
            entity_type="MediaAsset",
            entity_id=asset.id,
            entity_uuid=asset.uuid,
            message=rel,
        )
        return asset

    def add_video(
        self,
        work_order_id: int,
        source_path: Path,
        *,
        duration_seconds: int | None = None,
        actor_id: int | None = None,
    ) -> MediaAsset:
        work_order = self._work_orders.require_by_id(work_order_id)
        store = MediaStore(company_id=work_order.company_id, work_order_id=work_order.id)
        rel, size, checksum = store.save_file(source_path, prefix="video")
        asset = MediaAsset(
            company_id=work_order.company_id,
            work_order_id=work_order.id,
            media_type="video",
            category="other",
            phase="before",
            file_path=rel,
            original_name=source_path.name,
            file_size=size,
            checksum=checksum,
            duration_seconds=duration_seconds,
            captured_at=utc_now(),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(asset)
        self._session.flush()
        self._timeline_note(
            work_order.company_id,
            work_order.id,
            "Inspeksiya videosi qoʻshildi",
            actor_id,
        )
        return asset

    def hide_media(self, media_id: int, *, actor_id: int | None = None) -> MediaAsset:
        asset = self._session.get(MediaAsset, media_id)
        if asset is None or asset.deleted_at is not None:
            raise NotFoundError("Media topilmadi.", entity="MediaAsset")
        asset.is_hidden = True
        asset.updated_by = actor_id
        self._audit.record(
            "cx_media_hidden",
            actor_id=actor_id,
            entity_type="MediaAsset",
            entity_id=asset.id,
            entity_uuid=asset.uuid,
        )
        return asset

    def _timeline_note(
        self,
        company_id: int,
        work_order_id: int,
        title: str,
        actor_id: int | None,
    ) -> None:
        self._session.add(
            WorkOrderTimelineEvent(
                company_id=company_id,
                work_order_id=work_order_id,
                event_code=EVENT_NOTE_ADDED,
                visibility=VISIBILITY_STAFF,
                title=title,
                actor_id=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
