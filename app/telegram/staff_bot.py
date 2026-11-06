"""Staff-facing Telegram bot helpers (Mini App entry)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.core.exceptions import AppError
from app.modules.companies.models.company import Company
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.telegram.schemas import TelegramReplySchema
from app.modules.telegram.services.chat_service import TelegramChatService
from app.modules.users.models.user import User
from app.modules.work_orders.models.status import status_label
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.telegram.client import TelegramClient, TelegramClientError
from app.telegram.runtime_status import is_mini_app_online

logger = get_logger("telegram.staff")

BTN_UNREAD = "📬 Oʻqilmagan"
BTN_ORDERS = "📋 Buyurtmalar"
BTN_READY = "✅ Tayyor"
BTN_REPLY = "💬 Javob"
BTN_MENU = "🏠 Menyu"

STAFF_KEYBOARD: dict = {
    "keyboard": [
        [{"text": BTN_UNREAD}, {"text": BTN_ORDERS}],
        [{"text": BTN_READY}, {"text": BTN_REPLY}],
        [{"text": BTN_MENU}],
    ],
    "resize_keyboard": True,
}


def staff_web_app_keyboard(url: str) -> dict:
    """Reply keyboard with a single Mini App open button."""
    return {
        "keyboard": [
            [{"text": "📲 SMOXI ochish", "web_app": {"url": url}}],
        ],
        "resize_keyboard": True,
    }


def customer_portal_url(company: Company) -> str | None:
    """Return customer Mini App URL under the shared tunnel."""
    base = (company.telegram_mini_app_url or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}/customer/"


def customer_web_app_keyboard(url: str) -> dict:
    """Reply keyboard for the customer portal."""
    return {
        "keyboard": [
            [{"text": "📱 Mijoz kabineti", "web_app": {"url": url}}],
        ],
        "resize_keyboard": True,
    }


def staff_welcome(user: User, company: Company) -> str:
    url = (company.telegram_mini_app_url or "").strip()
    if url:
        return (
            f"<b>SMOXI — Xodim Mini App</b>\n"
            f"Kompaniya: {company.name}\n"
            f"Xodim: {user.full_name}\n\n"
            "Pastdagi <b>SMOXI ochish</b> tugmasini bosing "
            "yoki pastki menyudagi SMOXI ni tanlang."
        )
    return (
        f"<b>SMOXI — Xodim paneli</b>\n"
        f"Kompaniya: {company.name}\n"
        f"Xodim: {user.full_name}\n\n"
        "Mini App URL hali sozlanmagan.\n"
        "Sozlamalarga HTTPS manzilni yozing "
        "(cloudflared tunnel --url http://127.0.0.1:8765)."
    )


def sync_staff_menu_button(client: TelegramClient, company: Company) -> None:
    """Publish a safe global menu button for customers."""
    url = customer_portal_url(company)
    try:
        if url and is_mini_app_online():
            client.set_chat_menu_button(text="Kabinet", web_app_url=url)
            logger.info("Customer menu button yangilandi")
        else:
            client.clear_chat_menu_button()
    except TelegramClientError as exc:
        logger.warning("Menu button yangilanmadi: {}", exc)


def sync_chat_menu_button(
    client: TelegramClient,
    company: Company,
    *,
    chat_id: str,
    is_staff: bool,
) -> None:
    """Sync a per-chat menu button based on staff/customer role."""
    try:
        if is_staff:
            staff_url = (company.telegram_mini_app_url or "").strip()
            if staff_url and is_mini_app_online():
                client.set_chat_menu_button(
                    chat_id=chat_id,
                    text="SMOXI",
                    web_app_url=staff_url,
                )
            else:
                client.clear_chat_menu_button(chat_id=chat_id)
            return
        customer_url = customer_portal_url(company)
        if customer_url and is_mini_app_online():
            client.set_chat_menu_button(
                chat_id=chat_id,
                text="Kabinet",
                web_app_url=customer_url,
            )
        else:
            client.clear_chat_menu_button(chat_id=chat_id)
    except TelegramClientError as exc:
        logger.warning("Chat menu button yangilanmadi: {}", exc)


class StaffBotHandler:
    """Fallback text-button handler when Mini App URL is not configured."""

    def __init__(self, session: Session, *, company_id: int) -> None:
        self._session = session
        self._company_id = company_id
        self._states: dict[str, str] = {}
        self._reply_target: dict[str, str] = {}

    def attach_shared_state(
        self,
        states: dict[str, str],
        reply_target: dict[str, str],
    ) -> None:
        self._states = states
        self._reply_target = reply_target

    def handle(
        self,
        client: TelegramClient,
        company: Company,
        user: User,
        chat_id: str,
        text: str,
    ) -> None:
        text = (text or "").strip()
        if not text:
            return
        url = (company.telegram_mini_app_url or "").strip()
        if url:
            client.send_message(
                chat_id,
                staff_welcome(user, company),
                reply_markup=staff_web_app_keyboard(url),
            )
            return
        if text in {"/menu", "/start", BTN_MENU}:
            self._states[chat_id] = "idle"
            client.send_message(
                chat_id, staff_welcome(user, company), reply_markup=STAFF_KEYBOARD
            )
            return

        state = self._states.get(chat_id, "idle")
        if state == "reply_pick":
            self._pick_reply_chat(client, chat_id, text)
            return
        if state == "reply_text":
            self._send_reply(client, user, chat_id, text)
            return
        if state == "ready_pick":
            self._mark_ready(client, user, chat_id, text)
            return

        if text == BTN_UNREAD:
            self._show_unread(client, chat_id)
        elif text == BTN_ORDERS:
            self._show_orders(client, chat_id)
        elif text == BTN_REPLY:
            self._start_reply(client, chat_id)
        elif text == BTN_READY:
            self._start_ready(client, chat_id)
        else:
            client.send_message(
                chat_id,
                "Mini App URL sozlanmagan. Sozlamalarni tekshiring yoki /menu yuboring.",
                reply_markup=STAFF_KEYBOARD,
            )

    def _show_unread(self, client: TelegramClient, chat_id: str) -> None:
        notif = NotificationService(self._session)
        chat = TelegramChatService(self._session)
        unread_msgs = chat.count_unread(self._company_id)
        unread_notif = notif.count_unread(self._company_id)
        threads = [t for t in chat.list_threads(self._company_id) if t.unread_count > 0]
        lines = [
            "<b>Oʻqilmagan</b>",
            f"Xabarlar: {unread_msgs} · Bildirishnomalar: {unread_notif}",
            "",
        ]
        if not threads:
            lines.append("Hozircha oʻqilmagan suhbat yoʻq.")
        else:
            for thread in threads[:15]:
                lines.append(
                    f"• <b>{thread.customer_name}</b> ({thread.unread_count})\n"
                    f"  {thread.last_body}\n"
                    f"  chat: <code>{thread.chat_id}</code>"
                )
        client.send_message(chat_id, "\n".join(lines), reply_markup=STAFF_KEYBOARD)

    def _show_orders(self, client: TelegramClient, chat_id: str) -> None:
        orders = WorkOrderRepository(self._session).search(self._company_id, limit=15)
        if not orders:
            client.send_message(chat_id, "Buyurtmalar yoʻq.", reply_markup=STAFF_KEYBOARD)
            return
        lines = ["<b>Soʻnggi buyurtmalar</b>", ""]
        for order in orders:
            problem = (order.problem_description or "")[:60]
            lines.append(
                f"• <b>{order.number}</b> — {status_label(order.status)}\n"
                f"  {problem}"
            )
        client.send_message(chat_id, "\n".join(lines), reply_markup=STAFF_KEYBOARD)

    def _start_reply(self, client: TelegramClient, chat_id: str) -> None:
        threads = [
            t
            for t in TelegramChatService(self._session).list_threads(self._company_id)
            if t.unread_count > 0
        ]
        if not threads:
            threads = TelegramChatService(self._session).list_threads(self._company_id)[:10]
        if not threads:
            client.send_message(
                chat_id, "Javob berish uchun suhbat yoʻq.", reply_markup=STAFF_KEYBOARD
            )
            return
        lines = ["<b>Javob</b> — suhbat chat_id ni yuboring:", ""]
        for thread in threads[:12]:
            lines.append(
                f"• {thread.customer_name}: <code>{thread.chat_id}</code>\n"
                f"  {thread.last_body}"
            )
        self._states[chat_id] = "reply_pick"
        client.send_message(chat_id, "\n".join(lines))

    def _pick_reply_chat(self, client: TelegramClient, chat_id: str, text: str) -> None:
        target = text.strip().replace("`", "")
        if not target.lstrip("-").isdigit():
            client.send_message(chat_id, "Chat ID ni raqam koʻrinishida yuboring.")
            return
        self._reply_target[chat_id] = target
        self._states[chat_id] = "reply_text"
        client.send_message(chat_id, "Endi mijozga yuboriladigan javob matnini yozing.")

    def _send_reply(
        self, client: TelegramClient, user: User, chat_id: str, text: str
    ) -> None:
        target = self._reply_target.get(chat_id)
        if not target:
            self._states[chat_id] = "idle"
            client.send_message(chat_id, "Suhbat tanlanmadi.", reply_markup=STAFF_KEYBOARD)
            return
        try:
            TelegramChatService(self._session).reply(
                self._company_id,
                TelegramReplySchema(chat_id=target, body=text),
                actor_id=user.id,
            )
            NotificationService(self._session).mark_all_read(self._company_id)
        except (AppError, TelegramClientError) as exc:
            client.send_message(
                chat_id,
                f"Yuborilmadi: {exc}",
                reply_markup=STAFF_KEYBOARD,
            )
            self._states[chat_id] = "idle"
            return
        self._states[chat_id] = "idle"
        self._reply_target.pop(chat_id, None)
        client.send_message(chat_id, "✅ Javob yuborildi.", reply_markup=STAFF_KEYBOARD)

    def _start_ready(self, client: TelegramClient, chat_id: str) -> None:
        from app.modules.work_orders.models.status import WorkOrderStatus

        orders = WorkOrderRepository(self._session).search(self._company_id, limit=30)
        active = [
            o
            for o in orders
            if o.status
            in {
                WorkOrderStatus.WAITING_PARTS.value,
                WorkOrderStatus.REPAIRING.value,
                WorkOrderStatus.TESTING.value,
                WorkOrderStatus.QUALITY_CHECK.value,
            }
        ]
        if not active:
            client.send_message(
                chat_id,
                "Tayyor qilish mumkin boʻlgan buyurtma yoʻq.",
                reply_markup=STAFF_KEYBOARD,
            )
            return
        lines = ["<b>Tayyor</b> — buyurtma raqamini yuboring (masalan WO-000005):", ""]
        for order in active[:12]:
            lines.append(f"• <code>{order.number}</code> — {status_label(order.status)}")
        self._states[chat_id] = "ready_pick"
        client.send_message(chat_id, "\n".join(lines))

    def _mark_ready(
        self, client: TelegramClient, user: User, chat_id: str, text: str
    ) -> None:
        number = text.strip().upper()
        orders = WorkOrderRepository(self._session).search(
            self._company_id, query=number, limit=5
        )
        order = next((o for o in orders if o.number.upper() == number), None)
        if order is None:
            client.send_message(chat_id, "Buyurtma topilmadi. Raqamni tekshiring.")
            return
        try:
            result = WorkOrderService(self._session).mark_ready(
                order.id, actor_id=user.id
            )
        except AppError as exc:
            client.send_message(chat_id, exc.message, reply_markup=STAFF_KEYBOARD)
            self._states[chat_id] = "idle"
            return
        self._states[chat_id] = "idle"
        tg = {
            "sent": "Telegramga xabar yuborildi",
            "no_chat": "Mijoz botga ulanmagan",
            "no_token": "Bot token yoʻq",
        }.get(result.telegram_reason, result.telegram_reason)
        client.send_message(
            chat_id,
            f"✅ {result.work_order.number} tayyor.\n{tg}",
            reply_markup=STAFF_KEYBOARD,
        )
