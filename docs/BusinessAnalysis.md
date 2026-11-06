# SMOXI Service — Biznes Tahlili va Funksional Spetsifikatsiya

**Hujjat holati:** Rasmiy
**Versiya:** 1.0.0
**Sana:** 2026-07-23
**Til:** Oʻzbekcha (loyiha asosiy biznes va interfeys tili)
**Mahsulot:** SMOXI Service — xalqaro darajadagi Servis Boshqaruvi ERP

Bu hujjat SMOXI Service platformasining **rasmiy biznes tahlili va funksional spetsifikatsiyasi**dir.
Rivojlantirish jamoasi ushbu hujjat asosida mahsulotni qoʻshimcha biznes savollarsiz qurishi mumkin boʻlishi kerak.

> **Muhim:** Ushbu bosqichda dastur kodi, UI kodi va maʼlumotlar bazasi implementatsiyasi yaratilmaydi.
> **Til siyosati:** Dastur (foydalanuvchi interfeysi, xabarlar, hisobotlar, bildirishnomalar) **toʻliq oʻzbekcha** boʻladi. Boshqa tillar keyinchalik lokalizatsiya moduli orqali qoʻshiladi; asosiy (source) til — oʻzbekcha.

**Bogʻliq hujjatlar:**
[MasterDevelopmentPrompt.md](MasterDevelopmentPrompt.md) · [EngineeringStandards.md](EngineeringStandards.md) · [UIUXBlueprint.md](UIUXBlueprint.md) · [Roadmap.md](Roadmap.md) · [CustomerExperienceModule.md](CustomerExperienceModule.md)

---

## Mundarija

1. [Mahsulot maqsadi va koʻlami](#1-mahsulot-maqsadi-va-kōlami)
2. [Qoʻllab-quvvatlanadigan biznes turlari](#2-qōllab-quvvatlanadigan-biznes-turlari)
3. [Biznes maqsadlari](#3-biznes-maqsadlari)
4. [Asosiy tushunchalar va atamalar](#4-asosiy-tushunchalar-va-atamalar)
5. [Tashkilot modeli](#5-tashkilot-modeli)
6. [Toʻliq biznes jarayonlari](#6-tōliq-biznes-jarayonlari)
7. [Mijoz yoʻli (Customer Journey)](#7-mijoz-yōli-customer-journey)
8. [Xodim yoʻli (Employee Journey)](#8-xodim-yōli-employee-journey)
9. [Biznes qoidalari](#9-biznes-qoidalari)
10. [Status tizimi va oʻtishlar](#10-status-tizimi-va-ōtishlar)
11. [Funksional spetsifikatsiya (modullar)](#11-funksional-spetsifikatsiya-modullar)
12. [Bildirishnomalar va avtomatlashtirish](#12-bildirishnomalar-va-avtomatlashtirish)
13. [Hisobotlar va KPI](#13-hisobotlar-va-kpi)
14. [Xavfsizlik, audit va maʼlumotlarni saqlash](#14-xavfsizlik-audit-va-maʼlumotlarni-saqlash)
15. [Cheklovlar, taxminlar va ochiq masalalar](#15-cheklovlar-taxminlar-va-ochiq-masalalar)
16. [Kelajakdagi kengayish](#16-kelajakdagi-kengayish)

---

## 1. Mahsulot maqsadi va koʻlami

### 1.1 Maqsad

SMOXI Service — taʼmirlash va texnik xizmat koʻrsatish korxonalari uchun moʻljallangan **korporativ Servis Boshqaruvi ERP** platformasi. U bitta usta doʻkonidan tortib koʻp mamlakatli tarmoqgacha boʻlgan bizneslarni qoʻllab-quvvatlashi kerak.

### 1.2 Asosiy qiymat taklifi

| Qiymat | Natija |
|--------|--------|
| Har bir taʼmirni kuzatish | Yoʻqolgan buyurtma va “qayerda qurilma?” savollari kamayadi |
| Ombor va ehtiyot qismlar | Zaxira yetishmovchiligi va ortiqcha zaxira nazorati |
| Moliya shaffofligi | Har bir toʻlov, chegirma, soliq va foyda hisoblanadi |
| Offline ishlash | Internet boʻlmasa ham qabulxona ishlaydi |
| Kelajakdagi sinxronlash | Filiallar va bulut keyin ulanadi |
| Toʻliq oʻzbekcha interfeys | Mahalliy bozor uchun tayyor mahsulot |

### 1.3 Doira (Scope)

**Ichida:** autentifikatsiya, foydalanuvchilar/rollar, kompaniya/filiallar, mijozlar, qurilmalar, qabulxona, ish buyurtmalari (WO), diagnostika, taʼmir, kafolat, texniklar, ombor, yetkazib beruvchilar, xarid, hisob-fakturalar, toʻlovlar, xarajatlar, hisobotlar, kalendar, bildirishnomalar, sozlamalar, litsenziya, audit, zaxira nusxa.

**Tashqarida (hozircha):** toʻliq buxgalteriya (1C darajasida), ishlab chiqarish MRP, e-commerce doʻkon, umumiy CRM marketing avtomatlari — alohida plugin/modullar sifatida kelajakda.

### 1.4 Til siyosati (majburiy)

1. Barcha foydalanuvchi koʻradigan matnlar **oʻzbekcha**.
2. Status nomlari, tugmalar, xatolik xabarlari, cheklar, PDF hisobotlar — oʻzbekcha.
3. Ichki kod identifikatorlari (enum qiymatlari, ruxsat kalitlari) inglizcha `snake_case` boʻlishi mumkin; **koʻrinadigan yorliq** har doim oʻzbekcha.
4. Birinchi qoʻshimcha tillar: ruscha, inglizcha (keyingi fazalar).

---

## 2. Qoʻllab-quvvatlanadigan biznes turlari

Tizim **servis turi** sozlamasi orqali sozlanadi (maydonlar, shablonlar, kafolat muddatlari).

| Kategoriya | Misollar |
|------------|----------|
| Mobil va gadjet | Telefon, planshet, noutbuk, kompyuter |
| Elektronika | Televizor, printer, kamera, oʻyin pristavkalari |
| Transport | Avtoservis, mototsikl, velosiped |
| Uy jihozlari | Muzlatgich, kir yuvish, pechka |
| Muhandislik | HVAC, sanoat uskunalari |
| Maxsus | Tibbiy uskunalar |
| Xizmat | Tozalash, oʻrnatish, IT xizmat, maydon (field) servisi |
| Kelajak | Plugin orqali yangi vertikal modullar |

**Biznes qoidasi:** Bir kompaniyada bir nechta servis turi yoqilishi mumkin (masalan, telefon + noutbuk).

---

## 3. Biznes maqsadlari

| № | Maqsad | Oʻlchov (KPI) |
|---|--------|----------------|
| 1 | Mijoz kutish vaqtini qisqartirish | Oʻrtacha qabul vaqti, tayyor→topshirish vaqti |
| 2 | Texnik unumdorligini oshirish | Kunlik yopilgan WO soni, bandlik % |
| 3 | Har bir taʼmirni kuzatish | 100% WO da timeline va status tarixi |
| 4 | Har bir ehtiyot qismni kuzatish | Harakatlar jurnali, seriya/barcode |
| 5 | Har bir toʻlovni kuzatish | Toʻlov ↔ hisob-faktura bogʻlanishi |
| 6 | Xodim faoliyatini kuzatish | Audit jurnalı, kim nima oʻzgartirdi |
| 7 | Shaffoflik | Menejer dashboard, real vaqt KPI |
| 8 | Takroriy ishlarni avtomatlashtirish | Bildirishnoma, shablonlar, qoidalar |
| 9 | Offline ishlash | Internet yoʻqligida qabul/WO yaratish |
| 10 | Bulut sinxroni (kelajak) | `sync_status`, konfliktlar |
| 11 | Mobil / Telegram (kelajak) | Umumiy biznes model |
| 12 | Koʻp kompaniya / filial / ombor | Multi-tenant ichida tashkilot daraxti |
| 13 | Cheksiz foydalanuvchi va WO | Litsenziya oʻrindiqlari boʻyicha cheklov (tijorat) |

---

## 4. Asosiy tushunchalar va atamalar

| Atama (UZ) | Izoh |
|------------|------|
| **Kompaniya** | Yuridik shaxs / brend |
| **Filial** | Kompaniya ostidagi joylashuv |
| **Ombor** | Zaxira saqlash joyi (filialga bogʻliq yoki umumiy) |
| **Mijoz** | Jismoniy yoki yuridik shaxs |
| **Qurilma** | Taʼmirlanadigan obyekt (IMEI, seriya, model) |
| **Ish buyurtmasi (WO)** | Bitta taʼmir/xizmat ishi |
| **Qabulxona** | Qurilmani qabul qilish jarayoni |
| **Diagnostika** | Nosozlik aniqlash |
| **Smeta / Taklifnoma** | Taʼmir narxi va muddati |
| **Kafolat** | Topshirishdan keyingi majburiyat |
| **Texnik** | Taʼmirni bajaruvchi xodim |
| **Status tarixi** | Har bir status oʻzgarishi: kim, qachon, izoh |

---

## 5. Tashkilot modeli

```text
Kompaniya
 ├── Filial 1
 │    ├── Ombor A
 │    ├── Ombor B
 │    └── Foydalanuvchilar / rollar
 ├── Filial 2
 └── Markaziy ombor (ixtiyoriy)
```

**Qoidalar:**

1. Foydalanuvchi bir yoki bir nechta filialga biriktiriladi.
2. Ish buyurtmasi **bitta asosiy filialga** tegishli.
3. Omborlararo koʻchirish alohida hujjat orqali.
4. Hisobotlar filial yoki kompaniya darajasida filtrlanadi.
5. Multi-country: valyuta, soliq, manzil formatlari filial/kompaniya sozlamalarida.

---

## 6. Toʻliq biznes jarayonlari

### 6.1 Asosiy (baxtli) yoʻl — doʻkonda taʼmir

```text
Mijoz keladi
  → Qabulxona mijozni yaratadi/topadi
  → Qurilma roʻyxatdan oʻtkaziladi
  → Aksessuarlar yoziladi
  → Fotosuratlari olinadi
  → Mijoz qabul dalolatnomasini tasdiqlaydi (imzo/rozilik)
  → Ish buyurtmasi yaratiladi (Status: Qabul qilindi)
  → Texnik biriktiriladi
  → Diagnostika
  → Smeta tayyorlanadi
  → Mijoz roziligi
  → Agar tasdiqlansa → Taʼmir
  → Sinov
  → Sifat nazorati
  → Tayyor
  → Mijozga xabar
  → Topshirildi
  → Kafolat faollashtirildi
  → Yopildi
```

### 6.2 Muqobil jarayonlar

#### 6.2.1 Mijoz smetani rad etadi

```text
Smeta yuborildi → Mijoz rad etdi
  → Status: Rad etildi (yoki Yopishga tayyorlash)
  → Qurilma qaytarishga tayyorlanadi (taʼmirsiz)
  → Ixtiyoriy diagnostika haqi undiriladi (sozlama)
  → Topshirildi (taʼmirsiz) → Yopildi
```

**Biznes qoidasi:** Rad etilgan smetada ehtiyot qism bron qilingan boʻlsa — bron bekor qilinadi.

#### 6.2.2 Qurilma taʼmirlanmaydi

```text
Diagnostika → “Taʼmirlab boʻlmaydi”
  → Mijozga xabar + sabab
  → Variantlar: qaytarish / utilizatsiya / ehtiyot qism sifatida qabul (alohida ruxsat)
  → Status: Bekor qilindi yoki Yopildi (taʼmirlanmagan)
```

#### 6.2.3 Ehtiyot qism kutish

```text
Taʼmir / Diagnostika → Kerakli qism yoʻq
  → Status: Ehtiyot qism kutilyapti
  → Xarid buyurtmasi / ichki koʻchirish
  → Qism keldi → Ombor qabul
  → WO ga qaytarish → Taʼmirlanmoqda
```

#### 6.2.4 Taʼmir bekor qilindi

```text
Istalgan ochiq status → Bekor qilish soʻrovi
  → Sabab majburiy
  → Menejer tasdiqi (sozlamaga qarab)
  → Bronlar bekor · qisman toʻlovlar qaytarish jarayoni
  → Status: Bekor qilindi
```

#### 6.2.5 Kafolatli taʼmir

```text
Mijoz kafolat bilan keladi → Avvalgi WO / kafolat tekshiruvi
  → Yangi WO turi: Kafolat
  → Tasdiqlansa → Taʼmir (mijozdan taʼmir haqi olinmasligi mumkin)
  → Notoʻgʻri foydalanish aniqlansa → Oddiy taʼmirga oʻtkazish
```

#### 6.2.6 Takroriy taʼmir (qayta murojaat)

```text
Yopilgan WO dan keyin qisqa muddatda qayta nosozlik
  → Bogʻlangan WO yaratiladi (parent_wo)
  → Kafolat ichida / tashqarisida avtomatik aniqlanadi
```

#### 6.2.7 Favqulodda taʼmir

```text
Prioritet: Favqulodda
  → Navbat boshiga
  → Menejer/egaga bildirishnoma
  → Qisqa SLA
```

#### 6.2.8 Ekspress taʼmir

```text
Prioritet: Ekspress + qoʻshimcha toʻlov (sozlama)
  → Tezroq SLA
  → Alohida yorliq / rang
```

#### 6.2.9 Masofaviy qoʻllab-quvvatlash

```text
Murojaat (telefon/Telegram/ilova)
  → Masofaviy sessiyа yozuvi
  → Agar jismoniy taʼmir kerak boʻlsa → Oddiy WO ga aylantiriladi
```

#### 6.2.10 Joyida xizmat (on-site)

```text
Buyurtma → Manzil + vaqt
  → Texnik yuboriladi (kalendar)
  → Joyida diagnostika/taʼmir
  → Agar ustaxonaga olib ketish kerak → Transport holati + oddiy WO
```

#### 6.2.11 Olib ketish va yetkazib berish

```text
Pickup soʻrovi → Kuryer/texnik → Qabul
  → Taʼmir jarayoni
  → Delivery → Topshirish → Yopish
```

---

## 7. Mijoz yoʻli (Customer Journey)

Har bir bosqich: **Maqsad · Kutilgan natija · Bildirishnomalar · Kerakli maʼlumot · Muammolar · Biznes qoidalari · Kelajak avtomatlashtirish**

### 7.1 Birinchi aloqa / kelish

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Mijozni tizimga kiritish yoki topish |
| Natija | Mijoz kartochkasi tayyor |
| Bildirishnoma | Yoʻq (ichki) |
| Maʼlumot | F.I.Sh / kompaniya, telefon, ixtiyoriy email |
| Muammolar | Dublikat telefon |
| Qoidalar | Telefon noyoblik siyosati (filial yoki kompaniya doirasida) |
| Avtomatlashtirish | Telefon boʻyicha avtotopish |

### 7.2 Qurilmani topshirish (qabul)

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Qurilma holati va shartlarni qayd etish |
| Natija | Qabul dalolatnomasi + WO |
| Bildirishnoma | SMS/Telegram: “Qurilmangiz qabul qilindi, №…” |
| Maʼlumot | Model, seriya/IMEI, nosozlik, aksessuarlar, foto, parol (agar berilsa — maxfiy) |
| Muammolar | IMEI yoʻq, shikastlash bahsi |
| Qoidalar | Kamida 1 ta foto tavsiya; aksessuarlar roʻyxati majburiy boʻlishi mumkin (sozlama) |
| Avtomatlashtirish | Shablon nosozliklar, skaner |

### 7.3 Kutish / diagnostika

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Aniq smeta |
| Natija | Smeta tayyor |
| Bildirishnoma | “Diagnostika tugadi, smetani koʻring” |
| Maʼlumot | — |
| Muammolar | Mijoz javob bermaydi |
| Qoidalar | Javob bermasa N kundan keyin eslatma; M kundan keyin “javobsiz” jarayoni |
| Avtomatlashtirish | Avto-eslatmalar |

### 7.4 Smetani tasdiqlash / rad etish

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Rozilik olish |
| Natija | Tasdiqlangan yoki rad |
| Bildirishnoma | Tasdiq/rad natijasi qabulxonaga |
| Maʼlumot | Rozilik kanali: imzo, SMS kod, ogʻzaki (audit bilan) |
| Muammolar | Narx oʻzgarishi |
| Qoidalar | Tasdiqdan keyin narx oshsa — qayta tasdiq |
| Avtomatlashtirish | One-tap tasdiq (kelajak mobil/Telegram) |

### 7.5 Taʼmir jarayoni

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Ishni bajarish |
| Natija | Tayyor holat |
| Bildirishnoma | Muhim kechikishlar, qism kutish |
| Maʼlumot | — |
| Muammolar | Qoʻshimcha nosozlik |
| Qoidalar | Qoʻshimcha ish — yangi smeta qatori + tasdiq |
| Avtomatlashtirish | SLA ogohlantirishlari |

### 7.6 Olishga tayyor

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Mijozni chaqirish |
| Natija | Mijoz xabardor |
| Bildirishnoma | “Qurilma tayyor” |
| Maʼlumot | Filial manzili, ish vaqti |
| Muammolar | Mijoz kelmaydi |
| Qoidalar | Saqlash muddati sozlanadi; muddatdan keyin ombor haqi / eslatmalar |
| Avtomatlashtirish | Takroriy eslatma |

### 7.7 Topshirish va toʻlov

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Qurilmani qaytarish va pulni yopish |
| Natija | Topshirildi + toʻlov + kafolat |
| Bildirishnoma | Chek / kafolat eslatmasi |
| Maʼlumot | Toʻlov usuli, imzo |
| Muammolar | Qisman toʻlov, nizo |
| Qoidalar | Qarz bilan topshirish — faqat ruxsat bilan |
| Avtomatlashtirish | Fiskal chek integratsiyasi (kelajak) |

### 7.8 Kafolat davri

| Maydon | Mazmun |
|--------|--------|
| Maqsad | Kafolatli murojaatlarni boshqarish |
| Natija | Yangi kafolat WO yoki rad |
| Bildirishnoma | Natija |
| Maʼlumot | Avvalgi WO №, nosozlik |
| Muammolar | Notoʻgʻri foydalanish |
| Qoidalar | Kafolat muddati va shartlari majburiy |
| Avtomatlashtirish | Avtomatik muddat tekshiruvi |

---

## 8. Xodim yoʻli (Employee Journey)

### 8.1 Qabulxona xodimi

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Mijoz/qurilma qabul, WO ochish, aloqa, topshirish |
| Ruxsatlar | `customers.*` (koʻrish/yaratish), `reception.use`, `work_orders.create`, cheklangan tahrir |
| Kunlik ish | Navbat → qabul → smeta javoblari → topshirish → kassa yordami |
| KPI | Qabul vaqti, xato/qayta ishlash %, mijoz qoniqishi |
| Cheklov | Ombor tannarxini koʻrmasligi mumkin; bekor qilish — cheklangan |

### 8.2 Texnik

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Diagnostika, taʼmir, foto, qism soʻrovi, sinov |
| Ruxsatlar | Oʻziga biriktirilgan WO, status oʻtkazish (matritsa boʻyicha), qism sarflash |
| Kunlik ish | Board → ish olish → diagnostika → taʼmir → QC ga topshirish |
| KPI | Yopilgan ishlar, qayta taʼmir %, oʻrtacha vaqt |
| Cheklov | Narx/chegirma berolmasligi; boshqa texnik WO sini ochish — sozlama |

### 8.3 Ombor xodimi

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Kirim/chiqim, koʻchirish, inventarizatsiya, minimal zaxira |
| Ruxsatlar | `inventory.*`, `warehouse.*`, PO qabul |
| Kunlik ish | Qabul qilish → berish → ogohlantirishlar |
| KPI | Zaxira aniqlik, kutishdagi qismlar |
| Cheklov | Sotish narxini oʻzgartirish — cheklangan |

### 8.4 Hisobchi / kassir

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Hisob-faktura, toʻlov, kassa, xarajat, kun yopish |
| Ruxsatlar | `invoices.*`, `payments.*`, `finance.*` |
| Kunlik ish | Toʻlovlar → kassa → hisobot |
| KPI | Kassa farqi, debitor qarzdorlik |
| Cheklov | Audit yozuvlarini oʻchira olmaslik |

### 8.5 Menejer

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Navbat, tasdiqlar, KPI, nizolar, chegirmalar |
| Ruxsatlar | Koʻp modul `view` + tasdiq amallari |
| Kunlik ish | Dashboard → kechikkan WO → tasdiqlar |
| KPI | SLA bajarilishi, foyda, qayta taʼmir |
| Cheklov | Tizim sozlamalari / litsenziya — faqat admin |

### 8.6 Administrator

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Foydalanuvchilar, rollar, sozlamalar, zaxira, integratsiyalar |
| Ruxsatlar | `settings.*`, `admin.*` |
| Kunlik ish | Sozlamalar, muammolarni bartaraf etish |
| KPI | Uptime, muvaffaqiyatli zaxira |
| Cheklov | Oddiy operatsion WO oqimiga aralashmaslik (tavsiya) |

### 8.7 Egasi / rahbar

| Maydon | Mazmun |
|--------|--------|
| Masʼuliyat | Strategiya, moliyaviy koʻrinish, litsenziya |
| Ruxsatlar | Toʻliq hisobot + moliyaviy dashboard |
| Kunlik ish | KPI koʻrish, filiallarni solishtirish |
| KPI | Foyda, oʻsish, filiallar |
| Cheklov | — (lekin audit hammaga taalluqli) |

---

## 9. Biznes qoidalari

### 9.1 Mijoz

1. Har bir mijozda kamida bitta aloqa (telefon yoki email).
2. Dublikat telefon — ogohlantirish; birlashtirish faqat ruxsat bilan.
3. Yuridik mijozda STIR/soliq raqami maydonlari yoqilishi mumkin.
4. Mijozni “oʻchirish” — yumshoq oʻchirish; tarix saqlanadi.
5. Qora roʻyxat / kredit bloki — yangi WO ochishni toʻxtatishi mumkin.

### 9.2 Qurilma

1. Qurilma mijozga bogʻlangan (yoki kompaniya aktiviga).
2. IMEI/seriya — imkon qadar noyob.
3. Har bir taʼmir qurilma tarixiga yoziladi.
4. Parol/PIN — maxfiy maydon; auditda koʻrinmasligi kerak.

### 9.3 Taʼmir / Ish buyurtmasi

1. WO raqami tizimda noyob (filial prefiksi boʻlishi mumkin).
2. Har bir status oʻzgarishi tarixga yoziladi: foydalanuvchi, vaqt, izoh.
3. Taʼqiqlangan status oʻtishlari bloklanadi.
4. Ehtiyot qism sarfi ombor harakatini yaratadi.
5. Mehnat va qismlar smetasi alohida qatorlarda.
6. Prioritet: Oddiy / Ekspress / Favqulodda.

### 9.4 Kafolat

1. Topshirishda kafolat muddati boshlanadi (agar yoqilgan).
2. Kafolat turi: ish / qism / toʻliq.
3. Notoʻgʻri foydalanish — kafolatdan chiqarish (sabab majburiy).
4. Kafolat WO da mijoz toʻlovi odatda 0 (sozlama istisnolari bilan).

### 9.5 Inventar

1. Har bir harakat: kirim, chiqim, koʻchirish, inventarizatsiya, qaytarish.
2. Manfiy zaxira — sozlamaga qarab taqiqlanadi yoki ogohlantiriladi.
3. Minimal zaxira — ogohlantirish + xarid taklifi.
4. Seriyali qismlar alohida kuzatiladi.
5. Tannarx va sotish narxi alohida; tannarx ruxsat bilan.

### 9.6 Toʻlovlar

1. Toʻlov usullari: naqd, karta, oʻtkazma, aralash.
2. Toʻlov hisob-fakturaga taqsimlanadi.
3. Ortiqcha toʻlov — avans/kredit.
4. Kassa sessiya ochiq boʻlishi kerak (naqd uchun).

### 9.7 Hisob-fakturalar

1. Holatlar: Qoralama · Chiqarilgan · Toʻlangan · Qisman · Bekor · Kredit-nota.
2. Chiqarilgandan keyin muhim maydonlar qulflanadi.
3. WO dan avtomatik yaratish qoʻllab-quvvatlanadi.

### 9.8 Qaytarishlar (Refund)

1. Faqat ruxsat bilan.
2. Sabab majburiy.
3. Asl toʻlov bilan bogʻlanadi.
4. Kassa/hisobotlarga taʼsir qiladi.

### 9.9 Chegirmalar

1. Foiz yoki summa.
2. Limitlar rol boʻyicha (masalan, qabulxona max 5%, menejer 20%).
3. Chegirma auditga yoziladi.

### 9.10 Soliqlar

1. Soliq stavkalari sozlanadi (QQS va boshqalar).
2. Hisob-faktura qatorida soliq hisobi.
3. Filial/mamlakat boʻyicha farq.

### 9.11 Tasdiqlash jarayoni

1. Smeta tasdiqi mijozdan.
2. Katta chegirma / bekor qilish / qaytarish — ichki tasdiq.
3. Tasdiqchi, vaqt, qaror saqlanadi.

### 9.12 Bekor qilish

1. Sabab majburiy.
2. Bogʻliq bronlar bekor.
3. Toʻlovlar boʻlsa — qaytarish oqimi.

### 9.13 Maʼlumotlarni saqlash

1. Yumshoq oʻchirish default.
2. Audit jurnallari uzoq muddat saqlanadi (sozlama, masalan 3–7 yil).
3. Shaxsiy maʼlumotlarni eksport/oʻchirish soʻrovlari — admin jarayoni.

### 9.14 Audit

1. Login/logout, yaratish/yangilash/oʻchirish, status, moliyaviy amallar.
2. Audit yozuvlari o‘zgartirilmaydi.

### 9.15 Xavfsizlik

1. Parollar xeshlanadi.
2. RBAC.
3. Sessiya muddati + avto-chiqish.
4. Brute-force himoya.
5. Maxfiy maydonlar logda maskalanadi.

---

## 10. Status tizimi va oʻtishlar

### 10.1 Statuslar (oʻzbekcha yorliq)

| Kod (ichki) | Yorliq (UZ) | Maʼno |
|-------------|-------------|--------|
| `received` | Qabul qilindi | Qurilma qabul qilindi |
| `waiting_diagnosis` | Diagnostika kutilmoqda | Navbatda |
| `diagnosing` | Diagnostika qilinmoqda | Tekshiruv jarayoni |
| `waiting_customer_approval` | Mijoz roziligi kutilmoqda | Smeta yuborilgan |
| `approved` | Tasdiqlangan | Mijoz rozilik berdi |
| `waiting_parts` | Ehtiyot qism kutilyapti | Qism yoʻq |
| `repairing` | Taʼmirlanmoqda | Ish ketmoqda |
| `testing` | Sinovdan oʻtkazilmoqda | Funksional test |
| `quality_check` | Sifat nazorati | QC |
| `ready` | Tayyor | Olishga tayyor |
| `delivered` | Topshirildi | Mijozga berildi |
| `warranty` | Kafolatda | Kafolat holati (ixtiyoriy yorliq/yangi WO) |
| `closed` | Yopildi | Yakuniy |
| `cancelled` | Bekor qilindi | Bekor |
| `rejected` | Rad etildi | Smeta rad |
| `archived` | Arxivlangan | Uzoq muddatli arxiv |

### 10.2 Ruxsat etilgan oʻtishlar

```text
Qabul qilindi
  → Diagnostika kutilmoqda | Diagnostika qilinmoqda | Bekor qilindi

Diagnostika kutilmoqda
  → Diagnostika qilinmoqda | Bekor qilindi

Diagnostika qilinmoqda
  → Mijoz roziligi kutilmoqda | Ehtiyot qism kutilyapti | Rad etildi
  → Bekor qilindi | Taʼmirlanmaydi holati orqali Bekor/Yopish

Mijoz roziligi kutilmoqda
  → Tasdiqlangan | Rad etildi | Bekor qilindi

Tasdiqlangan
  → Ehtiyot qism kutilyapti | Taʼmirlanmoqda | Bekor qilindi

Ehtiyot qism kutilyapti
  → Taʼmirlanmoqda | Bekor qilindi | Mijoz roziligi kutilmoqda (narx oʻzgarsa)

Taʼmirlanmoqda
  → Sinovdan oʻtkazilmoqda | Ehtiyot qism kutilyapti | Bekor qilindi

Sinovdan oʻtkazilmoqda
  → Sifat nazorati | Taʼmirlanmoqda (qayta ishlash)

Sifat nazorati
  → Tayyor | Taʼmirlanmoqda (qayta)

Tayyor
  → Topshirildi | Taʼmirlanmoqda (qayta ochish, ruxsat bilan)

Topshirildi
  → Yopildi | Kafolatda (yoki alohida kafolat WO)

Kafolatda
  → Yopildi | Taʼmirlanmoqda (kafolat ishi)

Rad etildi
  → Topshirildi (taʼmirsiz qaytarish) | Yopildi | Bekor qilindi

Bekor qilindi
  → Arxivlangan

Yopildi
  → Arxivlangan | (Qayta ochish — faqat maxsus ruxsat)

Arxivlangan
  → (oʻqish; qayta ochish — admin)
```

**Umumiy qoidalar:**

1. Har bir oʻtishda ixtiyoriy/majburiy izoh (sozlama; bekor/rad — majburiy).
2. `version` maydoni bilan optimistik blokirovka.
3. Status tarixi hech qachon oʻchirilmaydi.

---

## 11. Funksional spetsifikatsiya (modullar)

Har bir modul uchun: maqsad, asosiy funksiyalar, asosiy obʼyektlar, ruxsatlar, bildirishnomalar.

### 11.1 Autentifikatsiya va xavfsizlik

- Login (kompaniya, login, parol), eslatib qolish, til (default oʻzbek), tema.
- Sessiya, avto-chiqish, bloklash.
- Parolni tiklash jarayoni.

### 11.2 Foydalanuvchilar, rollar, ruxsatlar

- Foydalanuvchi CRUD (yumshoq oʻchirish).
- Rollar: Qabulxona, Texnik, Ombor, Hisobchi, Menejer, Admin, Egasi (+ custom).
- Ruxsat matritsasi: `modul.amal`.

### 11.3 Kompaniya va filiallar

- Rekvizitlar, logo, ish vaqti, valyuta, soliq.
- Filiallar, omborlar bogʻlanishi.

### 11.4 Mijozlar

- Roʻyxat, kartochka, tarix, qurilmalar, toʻlovlar, hujjatlar, izohlar.

### 11.5 Qurilmalar

- Model/brend, identifikatorlar, holat, taʼmir tarixi.

### 11.6 Qabulxona

- Tezkor qabul formasi, skaner, foto, aksessuarlar, dalolatnoma chop etish.

### 11.7 Ish buyurtmalari

- Roʻyxat / Kanban / Kalendar.
- Timeline, fayllar, qism/mehnat, smeta, tasdiq, topshirish.

### 11.8 Texniklar

- Bandlik doskasi, koʻnikmalar, biriktirish, samaradorlik.

### 11.9 Inventar va ombor

- Tovarlar, kategoriyalar, harakatlar, minimal zaxira, barcode/QR, koʻchirish.

### 11.10 Yetkazib beruvchilar va xarid

- Yetkazib beruvchi kartochkasi, xarid buyurtmasi, qabul qilish.

### 11.11 Moliya

- Hisob-faktura, toʻlov, kassa, xarajat, qaytarish, kun yopish, soliq.

### 11.12 Hisobotlar

- Kunlik/haftalik/oylik/yillik, texnik KPI, mijoz, ombor, moliya; PDF/Excel/CSV.

### 11.13 Kalendar va bildirishnomalar

- Uchrashuvlar, eslatmalar, kanallar (ilova, Telegram kelajak, email kelajak).

### 11.14 Sozlamalar, litsenziya, zaxira

- Koʻrinish, lokalizatsiya (asosiy oʻzbek), zaxira/restore, yangilanish, litsenziya holati.

### 11.15 Audit jurnali

- Qidiruv, filtr, eksport (admin).

---

## 12. Bildirishnomalar va avtomatlashtirish

| Hodisa | Kimga | Kanal (1-bosqich / kelajak) |
|--------|-------|-----------------------------|
| WO qabul qilindi | Mijoz | Ilova ichida; SMS/Telegram kelajak |
| Smeta tayyor | Mijoz + qabulxona | Ichki + kelajak |
| Tasdiq/rad | Qabulxona / menejer | Ichki |
| Ehtiyot qism kutish uzoq | Menejer / ombor | Ichki |
| Tayyor | Mijoz | Ichki + kelajak |
| Minimal zaxira | Ombor | Ichki |
| Muvaffaqiyatsiz login | Admin | Ichki / xavfsizlik |
| Zaxira muvaffaqiyatsiz | Admin | Ichki |

Avtomatlashtirish qoidalari: shart → amal (status, eslatma, vazifa). 1-bosqichda oddiy shablonlar; keyin toʻliq Automation moduli.

---

## 13. Hisobotlar va KPI

| KPI | Izoh |
|-----|------|
| Bugungi qabul / tayyor / topshirilgan | Operatsion |
| Oʻrtacha taʼmir muddati | SLA |
| Qayta taʼmir foizi | Sifat |
| Daromad / xarajat / foyda | Moliya |
| Texnik yuklama | Resurs |
| Zaxira ogohlantirishlari | Ombor |
| Debitor qarzdorlik | Moliya |

Chop etish formatlari: A4, A5, termal chek, barcode/QR yorliqlar.

---

## 14. Xavfsizlik, audit va maʼlumotlarni saqlash

- Parol xeshlash, RBAC, sessiya, input validatsiya.
- Soft delete + audit maydonlari.
- Offline-first: mahalliy SQLite; sinxron maydonlari tayyor.
- Zaxira: avtomatik + qoʻlda; restore tasdiq bilan.
- Shaxsiy maʼlumotlar: minimal yigʻish, kirish nazorati.

---

## 15. Cheklovlar, taxminlar va ochiq masalalar

### Taxminlar (hujjatda qabul qilingan)

1. Asosiy UI tili — **oʻzbekcha**.
2. Birinchi platforma — Windows Desktop.
3. Bir filialli doʻkon ham, multi-filial ham bir modelda.
4. Fiskal apparat integratsiyasi 1-bosqichda majburiy emas.

### Ochiq masalalar (tasdiqlash kerak boʻlsa)

| № | Savol | Default (hozircha) |
|---|-------|---------------------|
| 1 | Diagnostika haqi smeta rad etilganda undiriladimi? | Sozlanadigan, default YOʻQ |
| 2 | Manfiy zaxira ruxsatimi? | YOʻQ |
| 3 | Qarz bilan topshirish? | Faqat menejer ruxsati |
| 4 | WO raqami formati? | `FILIAL-YYYYMMDD-XXXX` |
| 5 | Kafolat default muddati? | 30 kun (sozlanadi) |

Agar boshqacha kerak boʻlsa — shu hujjat yangilanadi, soʻngra kod.

---

## 16. Kelajakdagi kengayish

- Web, Android, iOS (bir xil biznes model).
- Telegram Mini App (status, tasdiq, tayyor xabar).
- Bulut PostgreSQL sinxronlash.
- AI yordamchi (diagnostika takliflari).
- Plugin tizimi (yangi vertikal bizneslar).
- Toʻliq API.

---

## Ilova A — Ruxsat nomlari (namuna)

`customers.view`, `customers.create`, `reception.use`, `work_orders.view`, `work_orders.create`, `work_orders.assign`, `work_orders.transition`, `work_orders.deliver`, `inventory.adjust`, `payments.create`, `finance.refund`, `settings.users`, `admin.audit`

---

## Ilova B — Majburiy maydonlar (biznes darajasi)

| Obʼyekt | Majburiy |
|---------|----------|
| Mijoz | Koʻrsatiladigan nom, telefon (yoki email) |
| Qurilma | Turi/model (yoki erkin nom), egasi |
| WO | Mijoz, qurilma yoki xizmat tavsifi, filial, ochilish sababi |
| Status oʻtishi | Yangi status; bekor/rad da izoh |
| Toʻlov | Summa, usul, kassa (naqd) |
| Hisob-faktura | Mijoz, qatorlar |

---

## Hujjat tarixi

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.0.0 | 2026-07-23 | Rasmiy BA & FS (5-bosqich), toʻliq oʻzbekcha |

---

*SMOXI Service — Biznes Tahlili va Funksional Spetsifikatsiya yakuni*
