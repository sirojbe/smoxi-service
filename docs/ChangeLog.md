# Changelog

All notable changes to SMOXI Service will be documented in this file.

## [1.12.0] — 2026-07-25

### Added

- **Filial filtri**: yangi WO ga `branch_id`; roʻyxatda faol filial / «Barcha filiallar»
- **Idle auto-lock**: Sozlamalar → daqiqa (0=off); faolsizlikdan keyin qulflash
- **RBAC sidebar**: rol ruxsatlariga qarab menyu yashirish

## [1.11.0] — 2026-07-24

### Added

- **Filiallar**: default MAIN, top bar tanlash, status bar
- **Qulflash**: ish stoli lock + parol bilan ochish / chiqish
- **Omborlar** sahifasi: CRUD + omborlararo zaxira oʻtkazish (`transfer`)

## [1.10.0] — 2026-07-24

### Added

- **Kompaniyalar (B2B)**: kredit limiti, hold, kontaktlar, mijoz bogʻlash (`business_clients`)
- **Litsenziya**: trial + kalit faollashtirish, oʻrinlar nazorati (Sozlamalar)
- **Foydalanuvchilar**: qoʻshish, rol, faol/oʻchirish, rollar matritsasi
- Login: «Parolni unutdingizmi?» yordam oynasi

### Changed

- Bootstrap: ruxsatlar/rollar yangilanishi + trial litsenziya

## [1.9.0] — 2026-07-24

### Added

- **Ctrl+K Global Search**: sahifalar, mijozlar, ish buyurtmalari
- **Mijozlar** sahifasi sidebarga ulandi (UIUX §2.1)
- **Boshqaruv** — audit jurnalini koʻrish
- Shell: yorugʻ/qorongʻu mavzu tugmasi

### Changed

- Yordam: Ctrl+K endi faol; sidebar tartibi Customers + Administration

## [1.8.1] — 2026-07-24

### Added

- **Yordam** va **Dastur haqida** sahifalari (UIUX §9.20)
- **Sinxronlash** UI: pending/conflict ko‘rish, synced/conflict belgilash

## [1.8.0] — 2026-07-24

### Added

- **REST API `/api/v1`**: health, login/me, work-orders, customers, sync pull/push
- **Sync foundation**: `SyncService` (pending WO/Customer pull + ack push)
- **Plugin registry**: `app/plugins` (core.sync, core.telegram discovery)
- `scripts/run_api.ps1` — API server (port 8787)
- Status bar: sync pending soni

## [1.7.0] — 2026-07-24

### Added

- **Avtomatlashtirish**: qoidalar (WO status / kam zaxira / qoʻlda), amallar (bildirishnoma / kalendar), tarix, namuna seed; READY va low-stock triggerlari
- **AI Yordamchi**: mahalliy KPI tavsiyalari + kalit soʻzli savol-javob (bulut LLM keyin)

### Changed

- Sidebar: Automation + AI Assistant (settings dan oldin)

## [1.6.1] — 2026-07-24

### Added

- Desktop **toast** (unread oshganda; quiet hours / kanal filtrlari bilan)
- Dashboard: soʻnggi oʻqilmagan bildirishnomalar + tezkor Kalendar/Bildirishnomalar
- Sozlamalar: bildirishnoma toast, quiet hours, kanal kalitlari (QSettings)

## [1.6.0] — 2026-07-24

### Added

- **Kalendar moduli**: oy/hafta/kun/kun tartibi, tadbir CRUD, soft-delete, sidebar `calendar`
- **Bildirishnomalar markazi**: filtrlar (Hammasi/Oʻqilmagan/Telegram/WO/Tizim/Sinxron); WO tayyor + kam zaxira eventlari
- **Paketlash**: `scripts/build_nuitka.ps1`, `scripts/build_installer.ps1`, `installer/smoxi.iss`
- **Mijoz Mini App (Feature 13)**: `/customer` portal — buyurtmalar, timeline, smeta tasdiq/rad, kafolat; xodim Mini App dan alohida auth

### Changed

- Sidebar tartibi: Reports → Calendar → Notifications → Telegram (UIUXBlueprint)

## [1.5.0] — 2026-07-24

### Added

- **CX-B…H implementatsiya** (Enterprise Customer Experience):
  - Qabul maydonlari (IMEI/SN/holat) + `IntakeSnapshot`, elektron imzo, qabul PDF
  - Foto/video media (`cx_media_assets`) + CX panel dialog
  - Smeta yuborish / mijoz roziligi gate + admin istisnosi (sabab majburiy)
  - Telegram `tg.cx.*` shablonlar + `NotificationDelivery` log
  - Ombor rezerv (tasdiq) va READY da yozib chiqarish
  - Topshirishda kafolat kartasi (PDF + timeline)
  - Hisobotlarda texnik KPI leaderboard
- Ish buyurtmalari: **CX panel** tugmasi (`CxHubDialog`)

### Changed

- `WorkOrderStatusChangeSchema.admin_override` — taʼmirni roziliksiz boshlash uchun
- Tezkor qabul CX maydonlarini `cx_intake_snapshots` ga yozadi

## [1.4.1] — 2026-07-24

### Added

- Rasmiy hujjat: **Enterprise Customer Experience (CX) Module** spetsifikatsiyasi — [docs/CustomerExperienceModule.md](CustomerExperienceModule.md) (kod/UI/DB yoʻq).
- **CX-A implementatsiya:** append-only taʼmir timeline (`work_order_timeline_events`), WO `public_token` + QR dialog (Ish buyurtmalari → Timeline / QR).
- Bildirishnomalar moduli: Telegram kiruvchi xabar → ichki bildirishnoma.
- Sidebar badge (Telegram / Bildirishnomalar) va yuqori panel qoʻngʻiroq.
- Telegram sahifasida oʻqilmagan banner va qalin suhbatlar.
- **Xodim Telegram paneli**: Sozlamalarda Telegram ID lar (`12646845,64665666`) — faqat shu ID lar xodim tugmalarini ochadi.
- **Xodim Telegram Mini App**: lokal FastAPI (port 8765) + avtomatik Cloudflare tunnel URL; pastki statusda bot holati.

## [1.4.0] — 2026-07-24

### Added

- Telegram inbox: mijoz xabarlari dasturga tushadi, xodim javob yozadi.
- «Tayyor» tugmasi oraliq statuslarni avtomatik o‘tkazadi va Telegramga xabar yuboradi.

### Changed

- Ish buyurtma raqami: `WO-000001` (doimiy ketma-ket, kunlik prefiks olib tashlandi).
- Telegram tasdiqdan keyin «sozlanmoqda» / «qism kutmoqda» xabari ham yuboriladi.

## [1.3.0] — 2026-07-23

### Added

- Tezkor qabul: telefon → avtomatik mijoz/WO ID, narx bilan Telegram tasdiq.
- Telegram bot: narx tasdiqlash/rad etish, sozlash va tayyor xabarlari.
- Sozlamalarda bot token/username; professional rangli light/dark UI.

## [1.2.0] — 2026-07-23

### Added

- Suppliers & Purchasing: supplier CRUD, purchase orders, receive into inventory.
- Sidebar route for Yetkazib beruvchilar.

## [1.1.0] — 2026-07-23

### Added

- Technicians module with work-order assignment.
- Reports module with live period stats, Excel and PDF export.
- Settings: company profile, users list, SQLite backup/restore.
- Dashboard live KPIs (repairs, waiting, revenue, low stock).

## [1.0.0] — 2026-07-23

### Added

- Finance module: invoices, payments, cash register open/close.
- Invoice from work order, partial/full payments, void rules.

## [0.9.0] — 2026-07-23

### Added

- Inventory module: warehouses, items, stock movements, low-stock filter.
- Stock in/out/adjust with negative-stock protection and movement history UI.

## [0.8.0] — 2026-07-23

### Added

- Reception desk: create work orders with customer/device/priority.
- Work Orders module: list, status filter, allowed transitions, status history.
- Status lifecycle per Business Analysis §10 with mandatory notes on cancel/reject.

## [0.7.0] — 2026-07-23

### Added

- Customers & Devices module: models, repositories, service, list UI, dialogs.
- Soft-delete customers/devices with audit events.
- Customer service unit tests.

### Changed

- Sidebar customers route opens full Customers page.

## [0.6.0] — 2026-07-23

### Added

- Platform Core: ORM base mixins, engine/session, Unit of Work, DI container, audit service.
- Security Foundation: User, Role, Permission, Company, sessions, AuthService, password hashing.
- Desktop Shell: login, main window, sidebar navigation, light/dark themes, oʻzbekcha i18n.
- Dashboard KPI placeholder page.
- Tests: platform core and authentication.

### Changed

- `main.py` launches PySide6 desktop application.
- Default locale `uz_UZ`.

## [0.5.0] — 2026-07-23

### Added

- Phase 5 rasmiy Biznes Tahlili va Funksional Spetsifikatsiya (`docs/BusinessAnalysis.md`, toʻliq oʻzbekcha).
- Cursor qoidasi: UI/biznes tili oʻzbekcha (`.cursor/rules/business-analysis.mdc`).
- Til siyosati: dastur interfeysi asosan oʻzbekcha.

## [0.4.0] — 2026-07-23

### Added

- Official Master Development Prompt v1.0 (`docs/MasterDevelopmentPrompt.md`).
- Cursor rule enforcing master delivery process (`.cursor/rules/master-development.mdc`).
- Recommended module delivery order in Roadmap.

## [0.3.0] — 2026-07-23

### Added

- Phase 3 official UI/UX Blueprint (`docs/UIUXBlueprint.md`).
- Cursor project rule enforcing UI/UX blueprint (`.cursor/rules/uiux-blueprint.mdc`).

## [0.2.0] — 2026-07-23

### Added

- Phase 2 official Engineering Standards (`docs/EngineeringStandards.md`).
- Cursor project rule enforcing standards (`.cursor/rules/engineering-standards.mdc`).

## [0.1.0] — 2026-07-23

### Added

- Phase 1 enterprise project foundation (structure, config starters, requirements, docs).
