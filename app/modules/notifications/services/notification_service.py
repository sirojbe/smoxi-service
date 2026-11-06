"""In-app notification application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.notifications.models.notification import InAppNotification
from app.modules.notifications.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Create and manage staff notifications."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._notifications = NotificationRepository(session)

    def count_unread(self, company_id: int) -> int:
        return self._notifications.count_unread(company_id)

    def list_notifications(
        self,
        company_id: int,
        *,
        unread_only: bool = False,
        kind: str | None = None,
    ) -> list[InAppNotification]:
        return self._notifications.list_for_company(
            company_id, unread_only=unread_only, kind=kind
        )

    def create(
        self,
        company_id: int,
        *,
        title: str,
        body: str,
        kind: str = "info",
        route: str | None = None,
        ref_key: str | None = None,
        customer_id: int | None = None,
        actor_id: int | None = None,
    ) -> InAppNotification:
        row = InAppNotification(
            company_id=company_id,
            title=title.strip()[:200],
            body=body.strip(),
            kind=kind,
            route=route,
            ref_key=ref_key,
            customer_id=customer_id,
            is_read=False,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self._notifications.add(row)

    def notify_work_order(
        self,
        company_id: int,
        *,
        title: str,
        body: str,
        work_order_id: int,
        actor_id: int | None = None,
    ) -> InAppNotification:
        return self.create(
            company_id,
            title=title,
            body=body,
            kind="work_order",
            route="work_orders",
            ref_key=str(work_order_id),
            actor_id=actor_id,
        )

    def notify_system(
        self,
        company_id: int,
        *,
        title: str,
        body: str,
        route: str | None = None,
        ref_key: str | None = None,
        actor_id: int | None = None,
    ) -> InAppNotification:
        return self.create(
            company_id,
            title=title,
            body=body,
            kind="system",
            route=route,
            ref_key=ref_key,
            actor_id=actor_id,
        )

    def notify_low_stock(
        self,
        company_id: int,
        *,
        item_name: str,
        quantity: int,
        item_id: int,
        actor_id: int | None = None,
    ) -> InAppNotification:
        return self.create(
            company_id,
            title=f"Kam zaxira: {item_name}",
            body=f"Qoldiq: {quantity}",
            kind="system",
            route="inventory",
            ref_key=str(item_id),
            actor_id=actor_id,
        )

    def notify_telegram_inbound(
        self,
        company_id: int,
        *,
        customer_name: str,
        chat_id: str,
        preview: str,
        customer_id: int | None = None,
    ) -> InAppNotification:
        text = preview.replace("\n", " ").strip()
        if len(text) > 120:
            text = text[:117] + "..."
        return self.create(
            company_id,
            title=f"Telegram: {customer_name}",
            body=text or "Yangi xabar",
            kind="telegram",
            route="telegram",
            ref_key=str(chat_id),
            customer_id=customer_id,
        )

    def mark_read(self, notification_id: int) -> None:
        self._notifications.mark_read(notification_id)

    def mark_all_read(self, company_id: int) -> int:
        return self._notifications.mark_all_read(company_id)
