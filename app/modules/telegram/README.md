# Telegram (mijoz chat + xodim Mini App)

Mijoz Telegram botga yozganda xabar dasturga tushadi; xodim javob yuboradi.
Status xabarlari (narx, sozlash, tayyor) ham shu bot orqali ketadi.

# Xodimlar uchun **Telegram Mini App** (web UI) dastur ichida `127.0.0.1:8765` da ishlaydi.
# HTTPS manzil **avtomatik** (cloudflared) olinadi va Sozlamaga yoziladi.

## Ochiq API

- `TelegramChatService` — suhbatlar, o‘qish, javob
- `TelegramPage` — inbox UI
- `TelegramPoller` — kiruvchi update (bog‘lash, tasdiq, chat)
- `app.telegram.miniapp` — xodim Mini App (FastAPI + static UI + auto tunnel)

## Xodim Mini App

1. Dasturni oching — pastki statusda **Bot: ishlayapti** / **ishlamayapti** koʻrinadi.
2. Mini App URL avtomatik yoziladi (birinchi marta cloudflared yuklanishi mumkin).
3. Xodim Telegram ID larini Sozlamalarga yozing.
4. Botga `/start` → **SMOXI ochish**.

## Qoidalar

- Soft-delete `telegram_messages`
- Javob faqat sozlangan bot token bilan
- Bog‘lanmagan chat avval telefon so‘raydi
- Kiruvchi xabarga avto-ack yuboriladi
- Mini App: `initData` HMAC + staff ID whitelist

## Oʻzgarishlar

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.4.1 | 2026-07-24 | Xodim Mini App + staff ID whitelist |
| 1.4.0 | 2026-07-24 | Ikki tomonlama chat + inbox |
