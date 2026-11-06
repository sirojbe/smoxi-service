# Customer Experience (CX)

Enterprise mijoz tajribasi moduli — qabul, media, imzo, PDF, timeline, smeta, Telegram, ombor rezerv, kafolat, texnik KPI.

Rasmiy FS: [`docs/CustomerExperienceModule.md`](../../../docs/CustomerExperienceModule.md).

## Ochiq API

| Servis | Vazifa |
|--------|--------|
| `TimelineService` | Append-only taʼmir timeline |
| `WorkOrderQrService` | `public_token` + QR payload |
| `IntakeService` | Intake snapshot, imzo, qabul PDF |
| `MediaService` | Foto/video saqlash |
| `QuoteService` | Smeta yuborish, admin override, rozilik gate |
| `ReservationService` | Qism rezerv / yozib chiqarish |
| `WarrantyService` | Topshirishda kafolat kartasi |
| `TechnicianKpiService` | Texnik leaderboard |
| `TelegramNotifier` | `tg.cx.*` shablonlar + `NotificationDelivery` |

## UI

- Ish buyurtmalari → **Timeline / QR** (`CxTimelineDialog`)
- Ish buyurtmalari → **CX panel** (`CxHubDialog`: smeta, media, imzo, PDF, kafolat, override)
- Tezkor qabul: IMEI/SN/holat maydonlari → snapshot
- Hisobotlar: texnik KPI jadvali

## Qoidalar

- Timeline oʻchirilmaydi
- Taʼmir (`repairing`) faqat mijoz roziligi yoki admin istisnosi (+ sabab) bilan
- Tasdiqdan keyin qismlar rezerv; READY da stock deduct
- DELIVERED → kafolat kartasi (PDF)
- Feature 13 (mijoz Mini App) — faqat arxitektura, kod yoʻq

## Oʻzgarishlar

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.1.0 | 2026-07-24 | CX-B…H: intake, media, quote, TG, rezerv, kafolat, KPI |
| 1.0.0 | 2026-07-24 | CX-A: timeline + QR |
