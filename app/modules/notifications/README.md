# Notifications

Xodimlar uchun ichki bildirishnomalar markazi.

## Ochiq API

- `NotificationService` — create, list (filter kind), unread count, mark read
- Producers: Telegram inbound, WO tayyor, kam zaxira
- `NotificationsPage` — filtrlash + ochish

## Filtrlar

`all` · `unread` · `telegram` · `work_order` · `system` · `sync`

## Oʻzgarishlar

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.1.0 | 2026-07-24 | Filtrlar + WO/inventory eventlari |
| 1.0.0 | 2026-07-24 | Asosiy markaz + Telegram inbound |
