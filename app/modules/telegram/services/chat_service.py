"""Telegram chat application service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.telegram.models.message import TelegramMessage
from app.modules.telegram.repositories.message_repository import TelegramMessageRepository
from app.modules.telegram.schemas import TelegramReplySchema
from app.services.audit_service import AuditService
from app.telegram.client import TelegramClient, TelegramClientError


@dataclass(frozen=True, slots=True)
class TelegramThreadView:
    """Thread row enriched with customer label."""

    chat_id: str
    customer_id: int | None
    customer_name: str
    customer_phone: str
    last_body: str
    last_at: object
    unread_count: int


class TelegramChatService:
    """Inbox list, read, record inbound, staff reply."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._messages = TelegramMessageRepository(session)
        self._customers = CustomerRepository(session)
        self._companies = CompanyRepository(session)
        self._audit = AuditService(session)

    def connection_status(self, company_id: int) -> tuple[bool, str]:
        """Return (configured, status_label_key_suffix)."""
        company = self._companies.get_by_id(company_id)
        if company is None:
            return False, "missing_company"
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            return False, "no_token"
        username = (company.telegram_bot_username or "").strip()
        return True, username or "configured"

    def list_threads(self, company_id: int) -> list[TelegramThreadView]:
        summaries = self._messages.list_threads(company_id)
        result: list[TelegramThreadView] = []
        for item in summaries:
            name = "—"
            phone = ""
            if item.customer_id is not None:
                customer = self._customers.get_by_id(item.customer_id)
                if customer is not None:
                    name = customer.display_name
                    phone = customer.phone
            else:
                customer = self._customers.get_by_telegram_chat_id(company_id, item.chat_id)
                if customer is not None:
                    name = customer.display_name
                    phone = customer.phone
            preview = item.last_body.replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            result.append(
                TelegramThreadView(
                    chat_id=item.chat_id,
                    customer_id=item.customer_id,
                    customer_name=name,
                    customer_phone=phone,
                    last_body=preview,
                    last_at=item.last_at,
                    unread_count=item.unread_count,
                )
            )
        return result

    def count_unread(self, company_id: int) -> int:
        return self._messages.count_unread(company_id)

    def list_messages(self, company_id: int, chat_id: str) -> list[TelegramMessage]:
        return self._messages.list_for_chat(company_id, chat_id)

    def mark_read(self, company_id: int, chat_id: str) -> None:
        self._messages.mark_chat_read(company_id, chat_id)

    def record_inbound(
        self,
        company_id: int,
        *,
        chat_id: str,
        body: str,
        customer_id: int | None = None,
        work_order_id: int | None = None,
        telegram_message_id: int | None = None,
        actor_id: int | None = None,
    ) -> TelegramMessage:
        text = (body or "").strip()
        if not text:
            raise ValidationError("Xabar matni boʻsh.")
        message = TelegramMessage(
            company_id=company_id,
            customer_id=customer_id,
            work_order_id=work_order_id,
            chat_id=str(chat_id),
            direction="inbound",
            body=text,
            telegram_message_id=telegram_message_id,
            is_read=False,
            is_auto=False,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._messages.add(message)
        return message

    def record_outbound(
        self,
        company_id: int,
        *,
        chat_id: str,
        body: str,
        customer_id: int | None = None,
        work_order_id: int | None = None,
        telegram_message_id: int | None = None,
        is_auto: bool = False,
        actor_id: int | None = None,
    ) -> TelegramMessage:
        message = TelegramMessage(
            company_id=company_id,
            customer_id=customer_id,
            work_order_id=work_order_id,
            chat_id=str(chat_id),
            direction="outbound",
            body=body,
            telegram_message_id=telegram_message_id,
            is_read=True,
            is_auto=is_auto,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._messages.add(message)
        return message

    def reply(
        self,
        company_id: int,
        payload: TelegramReplySchema,
        *,
        actor_id: int | None = None,
    ) -> TelegramMessage:
        company = self._companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Kompaniya topilmadi.", entity="Company")
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            raise ValidationError("Telegram bot token sozlanmagan.")

        customer = self._customers.get_by_telegram_chat_id(company_id, payload.chat_id)
        try:
            client = TelegramClient(token)
            result = client.send_message(payload.chat_id, payload.body)
        except TelegramClientError as exc:
            raise ValidationError(str(exc)) from exc

        tg_id = None
        raw = result.get("result") if isinstance(result, dict) else None
        if isinstance(raw, dict) and raw.get("message_id") is not None:
            try:
                tg_id = int(raw["message_id"])
            except (TypeError, ValueError):
                tg_id = None

        message = self.record_outbound(
            company_id,
            chat_id=payload.chat_id,
            body=payload.body.strip(),
            customer_id=customer.id if customer else None,
            telegram_message_id=tg_id,
            is_auto=False,
            actor_id=actor_id,
        )
        self._audit.record(
            "telegram_reply",
            actor_id=actor_id,
            entity_type="TelegramMessage",
            entity_id=message.id,
            entity_uuid=message.uuid,
            message=payload.chat_id,
        )
        return message

    def send_auto_ack(
        self,
        company_id: int,
        *,
        chat_id: str,
        customer_id: int | None,
        token: str,
    ) -> None:
        """Acknowledge inbound customer message."""
        text = "Xabaringiz qabul qilindi. Tez orada javob beramiz."
        try:
            client = TelegramClient(token)
            result = client.send_message(chat_id, text)
        except TelegramClientError:
            return
        tg_id = None
        raw = result.get("result") if isinstance(result, dict) else None
        if isinstance(raw, dict) and raw.get("message_id") is not None:
            try:
                tg_id = int(raw["message_id"])
            except (TypeError, ValueError):
                tg_id = None
        self.record_outbound(
            company_id,
            chat_id=chat_id,
            body=text,
            customer_id=customer_id,
            telegram_message_id=tg_id,
            is_auto=True,
        )
