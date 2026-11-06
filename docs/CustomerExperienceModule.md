# SMOXI Service — Enterprise Customer Experience (CX) Module

**Hujjat holati:** Rasmiy (binding) + implementatsiya **1.5.0** (CX-A…H)
**Versiya:** 1.1.0
**Sana:** 2026-07-24
**Kod nomi:** `CX` / `customer_experience`
**Til:** Oʻzbekcha (foydalanuvchi yorliqlari); ichki identifikatorlar inglizcha `snake_case`
**Mahsulot:** SMOXI Service — Enterprise Service Management ERP

> **Muhim:** Ushbu hujjat funksional va arxitektura spetsifikatsiyasidir.
> **CX-A…H** kod/UI/DB **1.5.0** da yetkazilgan.
> **Feature 13 (mijoz Mini App)** — **1.6.0**: `/customer` portal (Telegram initData + mijoz bogʻlanishi).

**Bogʻliq hujjatlar**

| Hujjat | Rol |
|--------|-----|
| [BusinessAnalysis.md](BusinessAnalysis.md) | Biznes qoidalari, status matritsasi, mijoz yoʻli |
| [UIUXBlueprint.md](UIUXBlueprint.md) | Shell, ekran shartnomalari (implementatsiya fazasida yangilanadi) |
| [EngineeringStandards.md](EngineeringStandards.md) | Clean Architecture, soft-delete, audit maydonlari |
| [MasterDevelopmentPrompt.md](MasterDevelopmentPrompt.md) | Modul yetkazib berish jarayoni |
| [Architecture.md](Architecture.md) | Tizim arxitekturasi |
| [Database.md](Database.md) | Persistensiya strategiyasi |

**Konfliktlar tartibi:** BusinessAnalysis statuslari va biznes qoidalari ustun; ushbu CX FS ularni chuqurlashtiradi, zid kelmasligi kerak. Ziddiyat boʻlsa — BA yangilanadi yoki CX FS tuzatiladi (docs PR).

---

## Mundarija

1. [Maqsad va mahsulot barasi](#1-maqsad-va-mahsulot-barasi)
2. [Modul chegarasi va integratsiyalar](#2-modul-chegarasi-va-integratsiyalar)
3. [CX tamoyillari](#3-cx-tamoyillari)
4. [Mantiqiy domen modeli](#4-mantiqiy-domen-modeli)
5. [Feature 1 — Qurilma qabul](#5-feature-1--qurilma-qabul)
6. [Feature 2 — Qurilma fotolari](#6-feature-2--qurilma-fotolari)
7. [Feature 3 — Video inspeksiya](#7-feature-3--video-inspeksiya)
8. [Feature 4 — Elektron imzo](#8-feature-4--elektron-imzo)
9. [Feature 5 — Avtomatik qabul PDF](#9-feature-5--avtomatik-qabul-pdf)
10. [Feature 6 — Taʼmir timeline](#10-feature-6--tamir-timeline)
11. [Feature 7 — Mijoz roziligi / smeta](#11-feature-7--mijoz-roziligi--smeta)
12. [Feature 8 — Telegram bildirishnomalar](#12-feature-8--telegram-bildirishnomalar)
13. [Feature 9 — Texnik unumdorligi](#13-feature-9--texnik-unumdorligi)
14. [Feature 10 — Ombor avtomatik hisobi](#14-feature-10--ombor-avtomatik-hisobi)
15. [Feature 11 — Kafolat kartasi](#15-feature-11--kafolat-kartasi)
16. [Feature 12 — QR kuzatuv](#16-feature-12--qr-kuzatuv)
17. [Feature 13 — Kelajak: Mijoz Mini App (faqat arxitektura)](#17-feature-13--kelajak-mijoz-mini-app-faqat-arxitektura)
18. [Feature 14 — Audit tizimi](#18-feature-14--audit-tizimi)
19. [Ekranlar, dialoglar, navigatsiya](#19-ekranlar-dialoglar-navigatsiya)
20. [Ruxsatlar matritsasi](#20-ruxsatlar-matritsasi)
21. [Hisobotlar](#21-hisobotlar)
22. [Xavfsizlik va ishlash](#22-xavfsizlik-va-ishlash)
23. [Fazalar va qabul mezonlari](#23-fazalar-va-qabul-mezonlari)
24. [Oʻzgarishlar tarixi](#24-ōzgarishlar-tarixi)

---

## 1. Maqsad va mahsulot barasi

### 1.1 Missiya

CX moduli mijozga **har bir bosqichda** qurilma holatini shaffof koʻrsatadi; xodimning har bir amali **timeline**ga avtomatik yoziladi; muhim voqealar **bildirishnoma** chaqiradi; taʼmir tarixi **doimiy** saqlanadi.

### 1.2 Muvaffaqiyat mezonlari (KPI)

| KPI | Maqsad |
|-----|--------|
| Status shaffofligi | 100% ochiq WO da joriy status + oxirgi timeline voqeasi |
| Qabul hujjati | 100% yangi WO da PDF + (imzo majburiy sozlamada) imzo |
| Foto qamrovi | Qabulda kamida sozlanadigan minimal foto toʻplami |
| Bildirishnoma yetkazilishi | Muhim voqealar uchun ≥ 95% muvaffaqiyatli yetkazish (retry bilan) |
| Nizo oldini olish | Imzo + foto/video + timeline biriktirilgan WO ulushi |
| Mijoz noaniqligi | “Holat nima?” qoʻngʻiroqlari kamayishi (operatsion metrika) |

### 1.3 Nima emas

- Demo yoki “faqat tugma” UX emas.
- Alohida CRM marketing platformasi emas.
- Toʻliq buxgalteriya 1C oʻrnini bosuvchi modul emas.
- Hozirgi fazada mijoz Telegram Mini App **implementatsiyasi** emas (faqat arxitektura tayyorgarligi).

---

## 2. Modul chegarasi va integratsiyalar

### 2.1 Ichki chegaralar

CX moduli quyidagilarni boshqaradi yoki qatʼiy kengaytiradi:

- Qabul (intake) jarayoni va qabul dalolatnomasi
- Mediya (foto, video), imzo, PDF arxiv
- Timeline voqealari va mijozga koʻrinadigan holat
- Smeta / mijoz roziligi oqimi
- CX bildirishnoma shablonlari va yetkazish tarixi
- Kafolat kartasi va QR kuzatuv
- Texnik CX KPI (hisobotlar bilan)
- Ombor rezerv/yozib chiqarish triggerlari (Inventory orqali)

### 2.2 Integratsiya nuqtalari

| Modul | Integratsiya |
|-------|----------------|
| **Customers** | Mijoz kartochkasi, telefon, email, kelajak Telegram |
| **Devices / Work Orders** | WO, qurilma, status oʻtishlari (BA §10) |
| **Inventory** | Rezerv, yozib chiqarish, ombor tarixi, seriya/QR |
| **Finance** | Smeta qatorlari, soliq, chegirma, invoice, toʻlov holati |
| **Reports** | CX KPI, texnik reyting, timeline eksport |
| **Telegram (mavjud)** | Mijoz bildirishnomalari, inbox; kelajak Mini App |
| **Notifications (ichki)** | Xodim bildirishnomalari |
| **Security / Audit** | Ruxsatlar, oʻzgarmas audit |

### 2.3 Clean Architecture (majburiy)

```text
UI (Reception / WO / CX screens)
  → Controllers / ViewModels
    → CX Application Services
      → Domain (Timeline, Media, Quote, Warranty, Signature)
        → Repositories → DB
        → Ports: Notifier, PdfRenderer, MediaStore, QrService
```

- UI da SQL/ORM yoʻq.
- Soft-delete: biznes jadvallarida `deleted_at`; timeline va audit **hard-delete taqiqlangan**.
- Standart audit maydonlari: EngineeringStandards boʻyicha.

---

## 3. CX tamoyillari

1. **Maksimal shaffoflik** — mijoz joriy bosqichni tushunadi.
2. **Minimal noaniqlik** — har bir kutish holati sabab + taxminiy muddat bilan.
3. **Tezkor aloqa** — muhim voqeada avtomatik xabar.
4. **Professional koʻrinish** — PDF, shablonlar, brend.
5. **Avtomatik hujjatlashtirish** — qoʻlda “eslab qolish”ga tayanmaslik.
6. **Qogʻozsiz oqim** — imzo, PDF, arxiv raqamli.
7. **Nizo oldini olish** — foto/video/imzo/timeline.
8. **Ishonch** — oʻzgarmas tarix, audit.
9. **Premium sifat** — majburiy QC bosqichi (sozlanadi).
10. **Enterprise masshtab** — koʻp filial, koʻp ombor, lokalizatsiya, DPI, light/dark.

---

## 4. Mantiqiy domen modeli

> Faqat **mantiqiy** obʼyektlar. Jismoniy CREATE TABLE ushbu hujjatda yoʻq.

| Obʼyekt | Maʼno |
|---------|--------|
| `WorkOrder` | Ish buyurtmasi (mavjud) |
| `IntakeSnapshot` | Qabul paytidagi toʻliq holat (qurilma + aksessuar + shartlar) |
| `MediaAsset` | Foto yoki video fayl + metadata + thumbnail |
| `CustomerSignature` | Elektron imzo + shartlar versiyasi (immutable) |
| `ReceiptDocument` | Qabul PDF (versiyali arxiv) |
| `TimelineEvent` | Taʼmir tarixidagi voqea (append-only) |
| `Quote` / `QuoteLine` | Smeta va qatorlar |
| `ApprovalDecision` | Tasdiq / rad / tushuntirish soʻrovi |
| `NotificationDelivery` | Telegram/SMS yetkazish urinishi |
| `PartReservation` | Ehtiyot qism rezervi |
| `WarrantyCard` | Kafolat kartasi |
| `WorkOrderQr` | WO QR payload / token |
| `TechnicianKpiSnapshot` | Davriy hisoblangan KPI (yoki on-the-fly view) |
| `AuditRecord` | Oʻzgarmas audit yozuvi |

### 4.1 Append-only qoidalar

- `TimelineEvent` — yangilash/oʻchirish taqiqlangan (faqat yangi voqea).
- `CustomerSignature` — tasdiqdan keyin oʻzgarmas.
- `AuditRecord` — oʻchirilmaydi.
- `MediaAsset` — “soft hide” mumkin; fayl saqlash siyosati boʻyicha hard-delete faqat maxsus retention job (admin).

---

## 5. Feature 1 — Qurilma qabul

### 5.1 Maqsad

Professional qabul jarayoni: mijoz, qurilma, holat, muammo, ustuvorlik — bitta WO ochilishi bilan.

### 5.2 Majburiy / ixtiyoriy maydonlar

| Maydon | Majburiy | Izoh |
|--------|----------|------|
| Mijoz | Ha | Mavjud yoki yangi |
| Telefon | Ha | Unikal soft-delete qoidasi BA bilan |
| Email | Yoʻq | Tavsiya |
| Telegram | Yoʻq | Kelajak bogʻlash |
| Qurilma kategoriyasi | Ha | |
| Brend | Ha | |
| Model | Ha | |
| Seriya raqami | Sozlama | |
| IMEI | Kategoriya boʻyicha | Mobil uchun tavsiya/majburiy |
| Rang | Yoʻq | |
| Sigʻim | Yoʻq | |
| Aksessuarlar | Checklist | Kamida “yoʻq” tanlanadi |
| SIM | Ha (bor/yoʻq) | |
| Memory card | Ha (bor/yoʻq) | |
| Batareya holati | Yoʻq | Enum |
| Ekran holati | Ha | Enum + izoh |
| Korpus holati | Ha | |
| Suv zarar indikatori | Yoʻq | |
| Oldingi taʼmirlar | Yoʻq | Matn |
| Muammo tavsifi | Ha | |
| Ichki izoh | Yoʻq | Mijozga koʻrinmaydi |
| Taxminiy tugash sanasi | Sozlama | |
| Ustuvorlik | Ha | `low/normal/high/urgent` |

### 5.3 Biznes qoidalari

1. Har bir muvaffaqiyatli qabul → noyob `WorkOrder.number` (kompaniya boʻyicha).
2. Har bir WO → noyob QR token (`Feature 12`).
3. Qabul yakunida majburiy: timeline `device_received`.
4. Sozlamada yoqilgan boʻlsa: foto minimal toʻplami, imzo, PDF avto-yaratish.
5. Ichki izoh mijoz kanaliga (Telegram/PDF mijoz nusxasi) chiqmaydi.

### 5.4 Workflow

```text
Mijoz qidirish/yaratish
  → Qurilma / holat / aksessuar
  → Muammo + ustuvorlik + muddat
  → (Foto/Video) → Imzo → PDF
  → WO yaratildi (received)
  → Timeline + Telegram “qabul qilindi”
```

### 5.5 Validatsiyalar

- Telefon normalizatsiyasi.
- IMEI format (agar majburiy).
- Muammo ≥ N belgi (sozlama, default 10).
- Urgent ustuvorlik uchun sabab izohi majburiy boʻlishi mumkin.

### 5.6 Ruxsatlar

- `reception.intake.create`
- `reception.intake.override_required_media` (manager+)

---

## 6. Feature 2 — Qurilma fotolari

### 6.1 Maqsad

Qabul va taʼmir davomida yuqori sifatli foto arxivi; nizo oldini olish; oldin/keyin solishtirish.

### 6.2 Kategoriyalar (enum)

`front`, `back`, `left`, `right`, `top`, `bottom`, `screen`, `camera`, `ports`, `damage`, `accessories`, `other`, `after_repair_*`

### 6.3 Biznes qoidalari

1. Original saqlanadi; thumbnail avtomatik.
2. Metadata: `captured_at`, `created_by`, `work_order_id`, `category`, `file_size`, `checksum`.
3. Tasodifiy oʻchirish yoʻq: UI da “oʻchirish” = soft-hide + audit; fizik fayl retention boʻyicha.
4. Cheksiz son (disk kvotasi sozlanadi; ogohlantirish).
5. `before` / `after` juftlik solishtirish UI.

### 6.4 Dialog / ekran

- Kamera/fayl tanlash, kategoriya, koʻp tanlov.
- Gallery: filtr (before/after), lightbox, zoom.

### 6.5 Xavfsizlik

- Fayl yoʻli UUID; toʻgʻridan-toʻgʻri path traversal yoʻq.
- Faqat ruxsatli rollar koʻradi; mijoz kanaliga faqat “mijozga ochiq” deb belgilanganlar.

---

## 7. Feature 3 — Video inspeksiya

### 6/7.1 Maqsad

Qisqa inspeksiya videosi: holat, displey, tugmalar, kamera, quvvat, ovoz — nizo dalili.

### 7.2 Metadata

| Maydon | Majburiy |
|--------|----------|
| Duration | Ha |
| Resolution | Ha |
| Created time | Ha |
| Employee | Ha |
| File size | Ha |
| Preview image | Ha (birinchi kadr/thumbnail) |
| Purpose tags | Yoʻq | `display`, `buttons`, `camera`, `charge`, `sound`, … |

### 7.3 Biznes qoidalari

1. Maksimal davomiylik sozlanadi (masalan 60–180 s).
2. Formatlar: MP4 tavsiya.
3. Kelajak cloud storage: `storage_backend` = `local` \| `cloud` (port).
4. Timeline voqeasi: `inspection_video_added`.

### 7.4 Validatsiya

- Boʻsh/buzilgan fayl rad.
- Minimal duration (masalan ≥ 3 s) sozlanadi.

---

## 8. Feature 4 — Elektron imzo

### 8.1 Maqsad

Mijoz qabul shartlarini elektron imzolaydi; hujjat WO ga yuridik bogʻlanadi.

### 8.2 Saqlanadigan maʼlumot

- Signature image / vector stroke data
- Date, time (UTC + local display)
- Employee (qabul qiluvchi)
- Work order, device snapshot id
- Acceptance terms **versiyasi** (matn hash)
- IP/machine — kelajak maydonlari (hozir ixtiyoriy)

### 8.3 Biznes qoidalari

1. Tasdiqlangandan keyin imzo **oʻzgartirilmaydi**.
2. Yangi imzo kerak boʻlsa — yangi versiya + timeline; eski saqlanadi.
3. Sozlamada “imzo majburiy” boʻlsa — PDF/WO yakunlash bloklanadi.
4. Shartlar matni lokalizatsiya kaliti orqali; versiya bump qoidalari.

### 8.4 Dialog

- Shartlarni oʻqish (scroll → “oʻqidim”).
- Canvas imzo.
- Tasdiqlash / bekor.

---

## 9. Feature 5 — Avtomatik qabul PDF

### 9.1 Tarkib

Kompaniya logo + maʼlumot; mijoz; qurilma; aksessuarlar; tanlangan fotolar (thumbnail grid); QR; WO raqami; qabul shartlari; imzo; taxminiy muddat; xodim.

### 9.2 Biznes qoidalari

1. WO yaratilganda yoki imzo tasdiqlanganda avto-generate (sozlama).
2. Chop etish layout + email-ready + arxiv.
3. Versiyali saqlash: qayta generatsiya yangi versiya yaratadi.
4. Kelajak: Telegram Mini App dan yuklab olish.

### 9.3 Integratsiya

- ReportLab/PDF port (EngineeringStandards).
- Email yuborish — kelajak yoki mavjud kanal.

---

## 10. Feature 6 — Taʼmir timeline

### 10.1 Maqsad

Toʻliq, yoʻqolmaydigan taʼmir tarixi. Har bir xodim amali → voqea.

### 10.2 Standart voqealar (kod → yorliq UZ)

| Kod | Yorliq |
|-----|--------|
| `device_received` | Qurilma qabul qilindi |
| `technician_assigned` | Texnik biriktirildi |
| `diagnosis_started` | Diagnostika boshlandi |
| `diagnosis_completed` | Diagnostika yakunlandi |
| `waiting_approval` | Rozilik kutilmoqda |
| `customer_approved` | Mijoz tasdiqladi |
| `customer_rejected` | Mijoz rad etdi |
| `waiting_parts` | Ehtiyot qism kutilmoqda |
| `repair_started` | Taʼmir boshlandi |
| `testing` | Sinov |
| `quality_control` | Sifat nazorati |
| `ready` | Tayyor |
| `delivered` | Topshirildi |
| `warranty_started` | Kafolat boshlandi |
| `closed` | Yopildi |
| `media_added` | Media qoʻshildi |
| `quote_updated` | Smeta yangilandi |
| `parts_reserved` | Qismlar rezerv qilindi |
| `parts_consumed` | Qismlar yozib chiqarildi |
| `note_added` | Izoh |
| `admin_override` | Admin istisnosi |

### 10.3 Har bir voqeada

- User, date, time
- Notes
- Attachments / images (ixtiyoriy)
- Location (kelajak)
- Related entity refs (`quote_id`, `media_id`, …)

### 10.4 Biznes qoidalari

1. Status oʻzgarishi **har doim** timeline voqeasi yaratadi.
2. Tarix hech qachon “yoʻqolmaydi” (append-only).
3. Mijozga koʻrinadigan / ichki voqealar flagi: `visibility = customer|staff|internal`.
4. BA §10 status matritsasiga zid oʻtishlar bloklanadi; blok ham auditga yozilishi mumkin.

### 10.5 UI

- WO detail: vertikal timeline (eng yangisi yuqorida yoki pastda — blueprint boʻyicha).
- Filtr: faqat mijozga ochiq / hammasi (staff).

---

## 11. Feature 7 — Mijoz roziligi / smeta

### 11.1 Smeta tarkibi

- Aniqlangan muammo
- Kerakli qismlar (qatorlar: nom, miqdor, narx)
- Mehnat haqi
- Soliq
- Chegirma
- Jami
- Taxminiy tugash

### 11.2 Mijoz variantlari

| Amal | Natija |
|------|--------|
| Approve | `approved` + timeline + taʼmirga ruxsat |
| Reject | `rejected` + timeline |
| Request explanation | Status saqlanadi; xodimga vazifa/notif; timeline `explanation_requested` |
| Ask question | Kelajak (chat) |

### 11.3 Biznes qoidalari

1. **Taʼmir boshlanishi taqiqlangan**, toki `customer_approved` yozilmaguncha — **admin override** dan tashqari.
2. Override: sabab majburiy + `admin_override` timeline + maxsus ruxsat.
3. Narx oʻzgarsa → yangi smeta versiyasi → qayta rozilik (BA bilan mos).
4. Chegirma limitlari rollar boʻyicha (BA §9).

### 11.4 Kanallar

- Desktop (telefon orqali qabulxona yozadi)
- Telegram callback/tasdiq (mavjud)
- Kelajak Mini App

---

## 12. Feature 8 — Telegram bildirishnomalar

### 12.1 Trigger voqealar

Device Received; Diagnosis Started/Completed; Quotation Ready; Approval Required; Repair Started; Additional Cost; Waiting Parts; Repair Completed; Ready for Pickup; Delivered; Warranty Activated.

### 12.2 Biznes qoidalari

1. Professional shablonlar (oʻzbekcha asos; multi-lang kelajak).
2. Brending: kompaniya nomi, logo (matn/kelajak).
3. Har bir urinish `NotificationDelivery` da: status, xato, retry count.
4. Failed → retry policy (masalan 3 marta, exponential backoff).
5. Chat bogʻlanmagan → “pending_link”; bogʻlangach flush (mavjud poller mantiqiga mos).
6. Ichki izohlar mijoz xabariga kirmaydi.

### 12.3 Shablon kalitlari (misol)

`tg.cx.received`, `tg.cx.quote_ready`, `tg.cx.ready`, …

---

## 13. Feature 9 — Texnik unumdorligi

### 13.1 Metrikalar

- Biriktirilgan / yakunlangan taʼmirlar
- Oʻrtacha taʼmir vaqti
- Oʻrtacha diagnostika vaqti
- Generatsiya qilingan daromad
- Mijoz reytingi (kelajak soʻrov)
- Kafolat qaytarishlari
- Takroriy taʼmirlar
- Productivity score (formula sozlanadi)
- Oylik reyting / leaderboard / KPI chart

### 13.2 Biznes qoidalari

1. Faqat ruxsatli rollar (manager/owner) toʻliq leaderboard koʻradi.
2. Texnik oʻz KPI sini koʻrishi mumkin (sozlama).
3. Hisobotlar moduli bilan bir xil sana filtri.

### 13.3 Hisobotlar

- Oylik texnik reyting PDF/Excel
- Drill-down: WO roʻyxati

---

## 14. Feature 10 — Ombor avtomatik hisobi

### 14.1 Oqim

```text
Taʼmir tasdiq (qismlar tanlandi)
  → PartReservation (reserv)
Repair completed / QC passed (sozlama nuqtasi)
  → Deduct stock
  → Warehouse history
  → Financial cost update
```

### 14.2 Biznes qoidalari

1. Manfiy zaxira taqiqlangan (yetarli boʻlmasa — blok + `waiting_parts`).
2. Koʻp ombor: WO filialiga bogʻlangan default ombor.
3. Seriyali qismlar: seriya majburiy.
4. Barcode/QR verification ixtiyoriy bosqich (sozlama).
5. Bekor/qaytarish: rezerv bekor yoki stock return workflow (alohida ruxsat).

### 14.3 Integratsiya

Faqat Inventory service orqali; CX toʻgʻridan-toʻgʻri stock jadvaliga yozmaydi.

---

## 15. Feature 11 — Kafolat kartasi

### 15.1 Tarkib

QR; Warranty Number; Customer; Device; Repair details; Installed parts; Period; Issue/Expiry; Terms; Digital verification; Printable PDF.

### 15.2 Biznes qoidalari

1. `delivered` yoki kafolat boshlanish nuqtasida avto-generate (sozlama).
2. Raqam kompaniya boʻyicha noyob.
3. Online verification — kelajak public endpoint.
4. Timeline: `warranty_started`.

---

## 16. Feature 12 — QR kuzatuv

### 16.1 Maqsad

Har bir WO QR; skan = joriy status, timeline (mijozga ochiq), fotolar (ochiq), kafolat, invoice, toʻlov holati, kompaniya, kelajak Mini App deep-link.

### 16.2 Biznes qoidalari

1. QR payload: imzolangan token yoki `wo_public_id` (taxmin qilinmaydigan).
2. Public view — faqat `visibility=customer` maʼlumot.
3. Ichki izohlar, tannarx, xodim telefoni — yashirin.
4. Qabul PDF va kafolat PDF ichida QR.

### 16.3 Xavfsizlik

- Token muddati / revoke (yoʻqolgan qurilma).
- Rate limit public endpoint (kelajak API).

---

## 17. Feature 13 — Kelajak: Mijoz Mini App (faqat arxitektura)

> **Implementatsiya yoʻq.** Faqat tayyorgarlik.

### 17.1 Mijoz portal imkoniyatlari

Repair Status; Timeline; Photos; Approval; Invoices; Warranty; PDF; Payments; Ratings; Messages; Notifications; Appointment; Support Chat.

### 17.2 Arxitektura eskizi

```text
Telegram Mini App (HTTPS)
  → BFF / Public CX API (read + approve)
    → Auth: Telegram initData + customer link
      → CX services (same domain as desktop)
        → DB (customer-visible projections)
```

### 17.3 Tayyorgarlik talablari (hozirgi dizayn)

1. Timeline `visibility` flaglari.
2. Document store (PDF) versiyalari.
3. Quote approval API kontrakti.
4. Deep-link: `wo/{public_id}` + bot.
5. Xodim Mini App dan **ajratilgan** mijoz Mini App (alohida route/permission).

---

## 18. Feature 14 — Audit tizimi

### 18.1 Har bir amal

Who; When; What changed; Old value; New value; Device/WO; IP (kelajak); Machine name.

### 18.2 Biznes qoidalari

1. Audit tarixi **oʻchirilmaydi**.
2. Soft-delete ham auditga yoziladi.
3. Maxfiy maydonlar maskalanadi (token, toʻliq imzo stroke ixtiyoriy).
4. CX voqealari `entity_type` + `entity_id` bilan bogʻlanadi.

---

## 19. Ekranlar, dialoglar, navigatsiya

> Implementatsiya fazasida `UIUXBlueprint.md` ga qoʻshiladi. Bu yerda talablar.

### 19.1 Taklif etilgan ekranlar

| ID | Ekran | Maqsad |
|----|-------|--------|
| CX-01 | Tezkor qabul (kengaytirilgan) | Feature 1–5 |
| CX-02 | WO CX panel | Timeline, media, smeta, QR |
| CX-03 | Media gallery | Foto/video |
| CX-04 | Imzo dialog | Feature 4 |
| CX-05 | Smeta dialog | Feature 7 |
| CX-06 | QR / kuzatuv preview | Feature 12 |
| CX-07 | Kafolat kartasi | Feature 11 |
| CX-08 | Texnik KPI | Feature 9 |
| CX-09 | Bildirishnoma yetkazish logi | Feature 8 |

### 19.2 Navigatsiya

- Asosiy kirish: Qabulxona + Ish buyurtmalari.
- KPI: Hisobotlar ostida yoki Texniklar.
- Global Search: WO raqami, IMEI, telefon.

### 19.3 UX qoidalari (blueprint)

- Light/Dark, oʻzbekcha matnlar, DPI.
- Toast muvaffaqiyat; soft-delete tasdiq.
- UI thread bloklanmasin (media/PDF background).

---

## 20. Ruxsatlar matritsasi

| Permission | Reception | Technician | Warehouse | Manager | Owner/Admin |
|------------|-----------|------------|-----------|---------|-------------|
| `cx.intake.create` | ✓ | | | ✓ | ✓ |
| `cx.media.upload` | ✓ | ✓ | | ✓ | ✓ |
| `cx.media.hide` | | | | ✓ | ✓ |
| `cx.signature.capture` | ✓ | | | ✓ | ✓ |
| `cx.quote.create` | ✓ | ✓ | | ✓ | ✓ |
| `cx.quote.approve_override` | | | | ✓ | ✓ |
| `cx.timeline.view_internal` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `cx.warranty.issue` | ✓ | | | ✓ | ✓ |
| `cx.kpi.view_all` | | | | ✓ | ✓ |
| `cx.audit.view` | | | | | ✓ |
| `cx.inventory.reserve` | | ✓ | ✓ | ✓ | ✓ |

---

## 21. Hisobotlar

| Hisobot | Tarkib |
|---------|--------|
| CX Qabul jurnali | Sana, WO, mijoz, xodim, imzo borligi, foto soni |
| Timeline eksport | WO boʻyicha voqealar |
| Bildirishnoma samaradorligi | Sent/fail/retry |
| Texnik KPI | Feature 9 |
| Kafolat reestri | Berilgan/muddati oʻtgan |
| Nizo paketi | Imzo+media+timeline birikmasi (export zip metadata) |

Filtr: sana oraligʻi, filial, texnik, status — Reports moduli bilan bir xil UX.

---

## 22. Xavfsizlik va ishlash

### 22.1 Xavfsizlik

- Ruxsatlar + soft-delete + append-only tarix.
- Media fayllar autentifikatsiyasiz URL bilan ochilmasin.
- QR public token taxmin qilinmasin.
- PII (telefon, IMEI) logda ehtiyot.
- Imzo va PDF arxiv backup ichida.

### 22.2 Ishlash

- Thumbnail async.
- Timeline sahifalash (cursor).
- PDF generation queue (katta foto grid).
- Video streaming/range (kelajak).
- Ombor rezerv concurrent: optimistic lock / version.

### 22.3 Offline

- Qabul offline mumkin (mavjud offline-first).
- Telegram keyin sync; media queue `pending_upload`.

---

## 23. Fazalar va qabul mezonlari

### 23.1 Tavsiya etilgan yetkazib berish tartibi

| Faza | Tarkib | Qabul mezoni |
|------|--------|--------------|
| **CX-A** | Timeline + status bogʻlanish + QR asos | **Done (1.4.1)** — har status → voqea; QR yaratiladi |
| **CX-B** | Intake maydonlari + PDF + imzo | **Done (1.5.0)** — snapshot, imzo lock, receipt PDF |
| **CX-C** | Foto/video | **Done (1.5.0)** — MediaService + CX panel |
| **CX-D** | Smeta/rozilik qoidalari + override | **Done (1.5.0)** — QuoteService + repairing gate |
| **CX-E** | Telegram CX shablonlari + delivery log | **Done (1.5.0)** — `tg.cx.*` + NotificationDelivery |
| **CX-F** | Ombor rezerv/deduct | **Done (1.5.0)** — rezerv on approve; consume on READY |
| **CX-G** | Kafolat kartasi | **Done (1.5.0)** — DELIVERED da PDF |
| **CX-H** | Texnik KPI | **Done (1.5.0)** — Hisobotlar KPI jadvali |
| **CX-I** | Mijoz Mini App arxitektura tekshiruvi | Kontraktlar tayyor (kod keyin) |

### 23.2 Doira tashqarida (shu modul spetsida emas)

- Toʻliq online toʻlov gateway
- AI diagnostika
- Marketing kampaniyalari

---

## 24. Oʻzgarishlar tarixi

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.1.0 | 2026-07-24 | CX-A…H implementatsiya qabul mezonlari Done (1.5.0); Feature 13 hali arxitektura |
| 1.0.0 | 2026-07-24 | Dastlabki Enterprise CX Functional Specification (kod/UI/DB yoʻq) |

---

## Ilova A — Bildirishnoma × Timeline matritsasi (qisqa)

| Timeline voqea | Mijoz Telegram | Ichki notif |
|----------------|----------------|-------------|
| `device_received` | ✓ | |
| `diagnosis_started` | ✓ (sozlama) | |
| `diagnosis_completed` | ✓ | |
| `waiting_approval` | ✓ | ✓ reception |
| `customer_approved` | ✓ | ✓ tech |
| `waiting_parts` | ✓ | ✓ warehouse |
| `repair_started` | ✓ | |
| `ready` | ✓ | ✓ reception |
| `delivered` | ✓ | |
| `warranty_started` | ✓ | |

---

## Ilova B — Qabul cheklist (operatsion)

1. Mijoz identifikatsiyasi
2. Qurilma identifikatsiyasi (IMEI/SN)
3. Holat + aksessuar checklist
4. Minimal foto toʻplami
5. (Ixtiyoriy) video
6. Shartlar + imzo
7. PDF chop/email
8. QR yorliq chop
9. Telegram bogʻlash / xabar

---

**Yakun:** Enterprise CX moduli **CX-A…H** yetkazilgan (1.5.0). Feature 13 mijoz Mini App — keyingi buyruq bilan.
