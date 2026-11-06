"""Customer-facing Telegram notification templates and send helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.modules.companies.models.company import Company
from app.modules.customers.models.customer import Customer
from app.modules.cx.models.cx_entities import NotificationDelivery
from app.modules.work_orders.models.work_order import WorkOrder
from app.telegram.client import TelegramClient, TelegramClientError

logger = get_logger("telegram.notifier")


class TelegramNotifier:
    """Send WO lifecycle messages to the customer Telegram chat."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _client_for_company(self, company: Company) -> TelegramClient | None:
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            return None
        try:
            return TelegramClient(token)
        except TelegramClientError:
            return None

    def _send(
        self,
        *,
        template_key: str,
        work_order: WorkOrder,
        customer: Customer,
        company: Company,
        text: str,
        reply_markup: dict | None = None,
    ) -> bool:
        client = self._client_for_company(company)
        chat_id = customer.telegram_chat_id
        if client is None or not chat_id:
            self._log_delivery(
                company_id=company.id,
                work_order_id=work_order.id,
                customer_id=customer.id,
                template_key=template_key,
                status="pending",
                chat_id=chat_id,
                error="no_token_or_chat",
            )
            return False
        try:
            client.send_message(chat_id, text, reply_markup=reply_markup)
            self._log_delivery(
                company_id=company.id,
                work_order_id=work_order.id,
                customer_id=customer.id,
                template_key=template_key,
                status="sent",
                chat_id=str(chat_id),
            )
            return True
        except TelegramClientError as exc:
            logger.warning("{} yuborilmadi: {}", template_key, exc)
            self._log_delivery(
                company_id=company.id,
                work_order_id=work_order.id,
                customer_id=customer.id,
                template_key=template_key,
                status="failed",
                chat_id=str(chat_id),
                error=str(exc),
            )
            return False

    def _log_delivery(
        self,
        *,
        company_id: int,
        work_order_id: int | None,
        customer_id: int | None,
        template_key: str,
        status: str,
        chat_id: str | None = None,
        error: str | None = None,
    ) -> None:
        try:
            self._session.add(
                NotificationDelivery(
                    company_id=company_id,
                    work_order_id=work_order_id,
                    customer_id=customer_id,
                    channel="telegram",
                    template_key=template_key,
                    status=status,
                    error_message=error,
                    chat_id=chat_id,
                    retry_count=0,
                )
            )
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Delivery log yozilmadi: {}", exc)

    def notify_quote(self, work_order: WorkOrder, customer: Customer, company: Company) -> bool:
        price = work_order.estimated_cost or 0
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Buyurtma: <b>{work_order.number}</b>\n"
            f"Mijoz: {customer.display_name}\n"
            f"Telefon: {customer.phone}\n\n"
            f"Xizmat narxi: <b>{price:,} soʻm</b>\n\n"
            f"Davom etish uchun pastdagi tugmani bosing."
        ).replace(",", " ")
        portal = self.customer_portal_url(company)
        markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Tasdiqlash", "callback_data": f"approve:{work_order.id}"},
                    {"text": "❌ Rad etish", "callback_data": f"reject:{work_order.id}"},
                ]
            ]
        }
        if portal:
            markup["inline_keyboard"].append(
                [{"text": "📱 Holatni koʻrish", "web_app": {"url": portal}}]
            )
        return self._send(
            template_key="tg.cx.quote_ready",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
            reply_markup=markup,
        )

    def customer_portal_url(self, company: Company) -> str | None:
        base = (company.telegram_mini_app_url or "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}/customer/"

    def notify_received(
        self, work_order: WorkOrder, customer: Customer, company: Company
    ) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Qurilmangiz qabul qilindi.\n"
            f"ID: <b>{work_order.number}</b>\n"
            f"Tez orada xabar beramiz."
        )
        return self._send(
            template_key="tg.cx.received",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )

    def notify_repairing(
        self, work_order: WorkOrder, customer: Customer, company: Company
    ) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Buyurtma <b>{work_order.number}</b>\n"
            f"Qurilmangiz hozir sozlanmoqda / taʼmirlanmoqda."
        )
        return self._send(
            template_key="tg.cx.repair_started",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )

    def notify_waiting_parts(
        self, work_order: WorkOrder, customer: Customer, company: Company
    ) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Buyurtma <b>{work_order.number}</b>\n"
            f"Ehtiyot qism kutilmoqda. Qism kelgach ish davom etadi."
        )
        return self._send(
            template_key="tg.cx.waiting_parts",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )

    def notify_ready(self, work_order: WorkOrder, customer: Customer, company: Company) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"🎉 Buyurtma <b>{work_order.number}</b> tayyor!\n"
            f"Qurilmangizni olib ketishingiz mumkin."
        )
        return self._send(
            template_key="tg.cx.ready",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )

    def notify_delivered(
        self, work_order: WorkOrder, customer: Customer, company: Company
    ) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Buyurtma <b>{work_order.number}</b> topshirildi.\n"
            f"Xizmatimizdan foydalanganingiz uchun rahmat!"
        )
        return self._send(
            template_key="tg.cx.delivered",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )

    def notify_warranty(
        self, work_order: WorkOrder, customer: Customer, company: Company
    ) -> bool:
        text = (
            f"<b>SMOXI Service</b>\n"
            f"Buyurtma <b>{work_order.number}</b> uchun kafolat faollashtirildi."
        )
        return self._send(
            template_key="tg.cx.warranty",
            work_order=work_order,
            customer=customer,
            company=company,
            text=text,
        )
