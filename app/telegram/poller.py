"""Background Telegram long-polling worker."""

from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.core.phone import digits_only, normalize_phone
from app.modules.companies.models.company import Company
from app.modules.companies.repositories.company_repository import CompanyRepository
from app.modules.customers.models.customer import Customer
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.settings.services.settings_service import SettingsService
from app.modules.work_orders.models.status import WorkOrderStatus
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.schemas.work_order_schema import WorkOrderStatusChangeSchema
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.telegram.client import TelegramClient, TelegramClientError
from app.telegram.notifier import TelegramNotifier
from app.telegram.runtime_status import is_mini_app_online
from app.telegram.staff_access import parse_staff_chat_ids
from app.telegram.staff_bot import (
    STAFF_KEYBOARD,
    StaffBotHandler,
    customer_portal_url,
    customer_web_app_keyboard,
    staff_web_app_keyboard,
    staff_welcome,
    sync_chat_menu_button,
    sync_staff_menu_button,
)

logger = get_logger("telegram.poller")

# One-tap phone share — customer does not type the number.
_CONTACT_KEYBOARD: dict = {
    "keyboard": [
        [
            {
                "text": "📱 Telefon raqamimni yuborish",
                "request_contact": True,
            }
        ]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}
_REMOVE_KEYBOARD: dict = {"remove_keyboard": True}
_MINI_APP_OFFLINE = (
    "Mini ilova hozir offline.\n"
    "Kompyuterdagi SMOXI dasturini ochib, Sozlamalarda yashil holatni kuting."
)


def _active_customer_portal(company: Company) -> str | None:
    portal = customer_portal_url(company)
    if portal and is_mini_app_online():
        return portal
    return None


def _bot_about_text(company: Company) -> str:
    """Welcome / about text shown on /start."""
    lines = [
        f"<b>{company.name}</b> — SMOXI Service boti",
        "",
        "Bu bot orqali:",
        "• Buyurtma narxini koʻrasiz va tasdiqlaysiz",
        "• Taʼmir holatini olasiz (sozlanmoqda, tayyor…)",
        "• Savol yozsangiz, servis javob beradi",
        "",
    ]
    if company.phone:
        lines.append(f"📞 Telefon: {company.phone}")
    if company.address:
        lines.append(f"📍 Manzil: {company.address}")
    if company.email:
        lines.append(f"✉️ Email: {company.email}")
    lines.append("")
    lines.append("Davom etish uchun pastdagi tugmani bosing — raqam avtomatik yuboriladi.")
    return "\n".join(lines)


def _customer_welcome_text(company: Company, customer_name: str) -> str:
    """Welcome text for linked customers using the shared bot."""
    return (
        f"<b>{company.name} — Mijoz kabineti</b>\n"
        f"Mijoz: {customer_name}\n\n"
        "Pastdagi tugma orqali buyurtma holati, timeline va rozilik oynasini oching."
    )


class TelegramPoller:
    """Poll bot updates and apply customer approve/reject decisions."""

    def __init__(self, container: ServiceContainer, *, company_id: int) -> None:
        self._container = container
        self._company_id = company_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset: int | None = None
        self._pending_phone: dict[str, str] = {}
        self._staff_states: dict[str, str] = {}
        self._staff_reply_target: dict[str, str] = {}
        self._synced_menu_url: str | None = None
        self._force_menu_sync = True

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="telegram-poller", daemon=True)
        self._thread.start()
        logger.info("Telegram poller ishga tushdi (company_id={})", self._company_id)

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
            except Exception as exc:  # noqa: BLE001 — keep worker alive
                logger.error("Telegram poller xatosi: {}", exc)
                time.sleep(3)

    def _poll_once(self) -> None:
        db = self._container.create_session()
        try:
            company = CompanyRepository(db).get_by_id(self._company_id)
            from app.security.secrets import company_bot_token

            token = company_bot_token(company) if company else ""
            if not token:
                time.sleep(5)
                return
            client = TelegramClient(token)
            current_url = (company.telegram_mini_app_url or "").strip() or None
            if self._force_menu_sync or current_url != self._synced_menu_url:
                sync_staff_menu_button(client, company)
                self._synced_menu_url = current_url
                self._force_menu_sync = False
            updates = client.get_updates(offset=self._offset, timeout=20)
            for update in updates:
                update_id = int(update.get("update_id", 0))
                self._offset = update_id + 1
                self._handle_update(db, client, company, update)
            db.commit()
        except TelegramClientError as exc:
            db.rollback()
            logger.warning("Telegram poll: {}", exc)
            time.sleep(5)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _handle_update(
        self,
        db: Session,
        client: TelegramClient,
        company: Company | None,
        update: dict,
    ) -> None:
        callback = update.get("callback_query")
        if callback:
            self._handle_callback(db, client, callback)
            return
        message = update.get("message") or update.get("edited_message")
        if message and company is not None:
            self._handle_message(db, client, company, message)

    def _handle_callback(self, db: Session, client: TelegramClient, callback: dict) -> None:
        data = str(callback.get("data") or "")
        callback_id = str(callback.get("id") or "")
        if ":" not in data:
            return
        action, raw_id = data.split(":", 1)
        try:
            work_order_id = int(raw_id)
        except ValueError:
            return
        service = WorkOrderService(db)
        try:
            if action == "approve":
                order = service.change_status(
                    work_order_id,
                    WorkOrderStatusChangeSchema(
                        to_status=WorkOrderStatus.APPROVED.value,
                        note="Telegram orqali tasdiqlandi",
                    ),
                    actor_id=None,
                    notify=True,
                    auto_advance=True,
                )
                client.answer_callback_query(callback_id, "Tasdiqlandi ✅")
                chat = callback.get("message", {}).get("chat", {})
                chat_id = chat.get("id")
                if chat_id is not None:
                    status_text = {
                        WorkOrderStatus.REPAIRING.value: "Qurilmangiz taʼmirlanmoqda.",
                        WorkOrderStatus.WAITING_PARTS.value: "Ehtiyot qism kutilmoqda.",
                        WorkOrderStatus.APPROVED.value: "Tasdiqlandi.",
                    }.get(order.status, "Tasdiqlandi.")
                    client.send_message(
                        chat_id,
                        f"✅ Narx tasdiqlandi.\nBuyurtma: <b>{order.number}</b>\n{status_text}",
                    )
            elif action == "reject":
                service.change_status(
                    work_order_id,
                    WorkOrderStatusChangeSchema(
                        to_status=WorkOrderStatus.REJECTED.value,
                        note="Telegram orqali rad etildi",
                    ),
                    actor_id=None,
                    notify=False,
                )
                client.answer_callback_query(callback_id, "Rad etildi")
                chat = callback.get("message", {}).get("chat", {})
                chat_id = chat.get("id")
                if chat_id is not None:
                    client.send_message(chat_id, "❌ Buyurtma rad etildi.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Callback ishlov berishda xato: {}", exc)
            try:
                client.answer_callback_query(callback_id, "Xatolik yuz berdi")
            except TelegramClientError:
                pass

    def _handle_message(
        self,
        db: Session,
        client: TelegramClient,
        company: Company,
        message: dict,
    ) -> None:
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        if not chat_id:
            return

        text = str(message.get("text") or "").strip()
        from_user = message.get("from") or {}
        from_id = str(from_user.get("id") or "").strip()
        # Baʼzi holatlarda chat.id va from.id farq qilishi mumkin — ikkalasini ham tekshiramiz
        candidate_ids = [cid for cid in (chat_id, from_id) if cid]

        # /id — haqiqiy Telegram ID ni koʻrsatish (xodim sozlash uchun)
        if text.lower() in {"/id", "/meningid", "id"}:
            allowed = parse_staff_chat_ids(company.telegram_staff_chat_ids)
            matched = any(cid in set(allowed) for cid in candidate_ids)
            lines = [
                f"Sizning Telegram ID: <code>{chat_id}</code>",
            ]
            if from_id and from_id != chat_id:
                lines.append(f"From ID: <code>{from_id}</code>")
            lines.append(
                "Xodim roʻyxatida: ✅ ha" if matched else "Xodim roʻyxatida: ❌ yoʻq"
            )
            if allowed:
                lines.append("Sozlamadagi ID lar: " + ", ".join(f"<code>{a}</code>" for a in allowed))
            else:
                lines.append("Sozlamada xodim ID lari hali yozilmagan.")
            lines.append(
                "\nShu <code>ID</code> ni nusxalab Sozlamalar → "
                "«Xodim Telegram ID lari» ga yozing va Saqlash bosing."
            )
            lines.append(
                "ID qoʻshilsa sizga xodim Mini App ochiladi; "
                "qoʻshilmasa bot mijoz kabineti sifatida ishlaydi."
            )
            client.send_message(chat_id, "\n".join(lines))
            return

        # Faqat Sozlamadagi Telegram ID lar xodim panelini ochadi
        staff_user = None
        for cid in candidate_ids:
            staff_user = SettingsService(db).resolve_staff_user(self._company_id, cid)
            if staff_user is not None:
                break
        if staff_user is None and company.telegram_staff_chat_ids:
            logger.info(
                "Xodim emas: chat_id={} from_id={} allowed={}",
                chat_id,
                from_id,
                company.telegram_staff_chat_ids,
            )
        sync_chat_menu_button(
            client,
            company,
            chat_id=chat_id,
            is_staff=staff_user is not None,
        )
        if staff_user is not None:
            url = (company.telegram_mini_app_url or "").strip()
            online = is_mini_app_online()
            markup = staff_web_app_keyboard(url) if url and online else STAFF_KEYBOARD
            if text.startswith("/start") or text.lower().startswith("/staff") or text == "/menu":
                message = staff_welcome(staff_user, company)
                if url and not online:
                    message = f"{message}\n\n{_MINI_APP_OFFLINE}"
                client.send_message(
                    chat_id,
                    message,
                    reply_markup=markup,
                )
                self._staff_states[chat_id] = "idle"
                return
            if url and online:
                # Mini App configured — nudge user to open it instead of text buttons
                client.send_message(
                    chat_id,
                    staff_welcome(staff_user, company),
                    reply_markup=markup,
                )
                return
            if url and not online:
                client.send_message(
                    chat_id,
                    f"{staff_welcome(staff_user, company)}\n\n{_MINI_APP_OFFLINE}",
                    reply_markup=markup,
                )
                return
            handler = StaffBotHandler(db, company_id=self._company_id)
            handler.attach_shared_state(self._staff_states, self._staff_reply_target)
            handler.handle(client, company, staff_user, chat_id, text)
            return

        # Ruxsat etilmagan ID /staff yuborsa
        if text.lower().startswith("/staff"):
            client.send_message(
                chat_id,
                "Bu Telegram ID xodimlar roʻyxatida yoʻq.\n"
                f"Sizning ID: <code>{chat_id}</code>\n"
                "Botga <code>/id</code> yuboring, chiqqan raqamni Sozlamalarga yozing.",
            )
            return

        customers = CustomerRepository(db)
        linked_customer = customers.get_by_telegram_chat_id(self._company_id, chat_id)
        customer_portal = _active_customer_portal(company)

        if text in {"/menu", "/start"} and linked_customer is not None:
            if customer_portal:
                client.send_message(
                    chat_id,
                    _customer_welcome_text(company, linked_customer.display_name),
                    reply_markup=customer_web_app_keyboard(customer_portal),
                )
            elif customer_portal_url(company):
                client.send_message(
                    chat_id,
                    f"{_customer_welcome_text(company, linked_customer.display_name)}\n\n{_MINI_APP_OFFLINE}",
                )
            if text == "/menu":
                return

        contact = message.get("contact")
        if contact and contact.get("phone_number"):
            # Faqat o‘z kontaktini qabul qilamiz (boshqa odamnikini emas).
            from_user = message.get("from") or {}
            contact_user_id = contact.get("user_id")
            if contact_user_id is not None and from_user.get("id") is not None:
                if int(contact_user_id) != int(from_user["id"]):
                    client.send_message(
                        chat_id,
                        "Iltimos, o‘zingizning telefon raqamingizni yuboring "
                        "(pastdagi tugma orqali).",
                        reply_markup=_CONTACT_KEYBOARD,
                    )
                    return
            self._link_phone_and_notify(
                db,
                client,
                company,
                chat_id,
                str(contact["phone_number"]),
            )
            return

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            payload = parts[1].strip() if len(parts) > 1 else ""
            # Avval bot haqida ma’lumot
            client.send_message(chat_id, _bot_about_text(company))

            if payload.startswith("p") and len(payload) > 1:
                self._link_phone_and_notify(db, client, company, chat_id, payload[1:])
                return
            if payload.startswith("w") and payload[1:].isdigit():
                self._link_work_order_and_notify(
                    db, client, company, chat_id, int(payload[1:])
                )
                return

            if linked_customer is not None and customer_portal:
                client.send_message(
                    chat_id,
                    _customer_welcome_text(company, linked_customer.display_name),
                    reply_markup=customer_web_app_keyboard(customer_portal),
                )
                return

            # Qo‘lda yozmasin — kontakt tugmasi
            client.send_message(
                chat_id,
                "Telefon raqamingizni <b>yozmang</b> — pastdagi tugmani bosing.",
                reply_markup=_CONTACT_KEYBOARD,
            )
            self._pending_phone[chat_id] = "await_phone"
            return

        if self._pending_phone.get(chat_id) == "await_phone" or text.startswith("+") or (
            text.isdigit() and len(digits_only(text)) >= 9
        ):
            # Fallback: hali ham matn yuborsa qabul qilamiz, lekin tugmani eslatamiz.
            phone = text.replace(" ", "")
            if len(digits_only(phone)) < 9:
                client.send_message(
                    chat_id,
                    "Raqamni yozmang. Pastdagi «Telefon raqamimni yuborish» tugmasini bosing.",
                    reply_markup=_CONTACT_KEYBOARD,
                )
                return
            self._link_phone_and_notify(db, client, company, chat_id, phone)
            return

        # Free-text from linked customer → inbox + auto-ack
        if text:
            self._store_inbound_chat(db, client, company, chat_id, message, text)

    def _store_inbound_chat(
        self,
        db: Session,
        client: TelegramClient,
        company: Company,
        chat_id: str,
        message: dict,
        text: str,
    ) -> None:
        from app.modules.telegram.services.chat_service import TelegramChatService

        customer = CustomerRepository(db).get_by_telegram_chat_id(self._company_id, chat_id)
        if customer is None:
            client.send_message(
                chat_id,
                "Avval telefon raqamingizni yuboring.\n"
                "Pastdagi tugmani bosing yoki /start yuboring.",
                reply_markup=_CONTACT_KEYBOARD,
            )
            self._pending_phone[chat_id] = "await_phone"
            return

        tg_msg_id = message.get("message_id")
        try:
            tg_id = int(tg_msg_id) if tg_msg_id is not None else None
        except (TypeError, ValueError):
            tg_id = None

        chat = TelegramChatService(db)
        chat.record_inbound(
            self._company_id,
            chat_id=chat_id,
            body=text,
            customer_id=customer.id,
            telegram_message_id=tg_id,
        )
        from app.modules.notifications.services.notification_service import (
            NotificationService,
        )

        NotificationService(db).notify_telegram_inbound(
            self._company_id,
            customer_name=customer.display_name,
            chat_id=chat_id,
            preview=text,
            customer_id=customer.id,
        )
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if token:
            chat.send_auto_ack(
                self._company_id,
                chat_id=chat_id,
                customer_id=customer.id,
                token=token,
            )

    def _link_phone_and_notify(
        self,
        db: Session,
        client: TelegramClient,
        company: Company,
        chat_id: str,
        phone: str,
    ) -> None:
        customers = CustomerRepository(db)
        customer = customers.get_by_phone(self._company_id, phone)
        if customer is None:
            client.send_message(
                chat_id,
                "Bu telefon bazada topilmadi.\n"
                "Avval qabulxonaga murojaat qiling — keyin shu botni oching.",
                reply_markup=_CONTACT_KEYBOARD,
            )
            return
        customer.telegram_chat_id = chat_id
        customer.phone = normalize_phone(customer.phone)
        customers.save(customer)
        self._pending_phone.pop(chat_id, None)
        client.send_message(
            chat_id,
            f"✅ Bogʻlandi: <b>{customer.display_name}</b>\n"
            f"Telefon: {customer.phone}\n"
            "Endi buyurtma xabarlari avtomatik keladi.",
            reply_markup=_REMOVE_KEYBOARD,
        )
        portal = _active_customer_portal(company)
        if portal:
            client.send_message(
                chat_id,
                _customer_welcome_text(company, customer.display_name),
                reply_markup=customer_web_app_keyboard(portal),
            )
        self._flush_pending_notifications(db, company, customer)

    def _link_work_order_and_notify(
        self,
        db: Session,
        client: TelegramClient,
        company: Company,
        chat_id: str,
        work_order_id: int,
    ) -> None:
        order = WorkOrderRepository(db).get_by_id(work_order_id)
        if order is None or order.company_id != self._company_id:
            client.send_message(chat_id, "Buyurtma topilmadi.")
            return
        customers = CustomerRepository(db)
        customer = customers.get_by_id(order.customer_id)
        if customer is None:
            client.send_message(chat_id, "Mijoz topilmadi.")
            return
        customer.telegram_chat_id = chat_id
        customers.save(customer)
        client.send_message(
            chat_id,
            f"✅ Buyurtma <b>{order.number}</b> uchun bogʻlandingiz.\n"
            "Endi xabarlar avtomatik keladi.",
            reply_markup=_REMOVE_KEYBOARD,
        )
        portal = _active_customer_portal(company)
        if portal:
            client.send_message(
                chat_id,
                _customer_welcome_text(company, customer.display_name),
                reply_markup=customer_web_app_keyboard(portal),
            )
        self._flush_pending_notifications(
            db, company, customer, preferred_wo_id=order.id
        )

    def _flush_pending_notifications(
        self,
        db: Session,
        company: Company,
        customer: Customer,
        *,
        preferred_wo_id: int | None = None,
    ) -> None:
        """Send waiting quote / latest received notice after linking."""
        notifier = TelegramNotifier(db)
        orders = WorkOrderRepository(db).list_for_customer(customer.id)
        ordered = sorted(
            orders,
            key=lambda o: (
                0 if preferred_wo_id is not None and o.id == preferred_wo_id else 1,
                0 if o.status == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value else 1,
                -(o.id or 0),
            ),
        )
        for order in ordered[:3]:
            if order.status == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value:
                if notifier.notify_quote(order, customer, company):
                    return
            if order.status == WorkOrderStatus.RECEIVED.value:
                if notifier.notify_received(order, customer, company):
                    return


def start_telegram_poller(
    container: ServiceContainer,
    company_id: int,
    *,
    holder: list[TelegramPoller],
) -> TelegramPoller:
    """Start (or replace) the company poller kept in *holder*."""
    if holder:
        holder[0].stop()
        holder.clear()
    poller = TelegramPoller(container, company_id=company_id)
    poller.start()
    holder.append(poller)
    return poller
