# Ish buyurtmalari moduli

Qabulxona orqali WO yaratish va toʻliq status lifecycle.

## Statuslar

Business Analysis §10 ga mos: `received` → … → `closed` / `archived`.

## Ochiq API

- `WorkOrderService.create_from_reception`
- `WorkOrderService.change_status`
- `WorkOrderService.mark_ready` / `mark_delivered`
- `ReceptionPage`, `WorkOrdersPage`

## Oʻzgarishlar

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.13.1 | 2026-07-31 | Tezkor «Mijozga topshirish» (ready→delivered) + Mini App |
| 0.8.0 | 2026-07-23 | Qabulxona + WO lifecycle |
