# SMOXI Service — Enterprise UI/UX Blueprint

**Document status:** Official
**Version:** 1.0.0
**Effective date:** 2026-07-23
**Applies to:** All screens, dialogs, navigation, and UX flows
**Primary platform:** Windows Desktop (PySide6)
**Future platforms:** Web, Android, iOS (shared IA & design tokens)

This document is the **mandatory UI/UX specification** for SMOXI Service.
Every future screen, menu, button, dialog, and workflow **must** follow it.

> **Phase 3 note:** Design and specification only. No application code, no database tables, no runtime implementation.

**Related:** [EngineeringStandards.md](EngineeringStandards.md) · [BusinessAnalysis.md](BusinessAnalysis.md) · [Architecture.md](Architecture.md) · [Roadmap.md](Roadmap.md)

**Til:** Foydalanuvchi interfeysi asosiy tili — **oʻzbekcha** (`uz_UZ`). Boshqa tillar keyinchalik.

---

## Table of Contents

1. [Product Vision & UX Principles](#1-product-vision--ux-principles)
2. [Information Architecture](#2-information-architecture)
3. [Application Shell & Main Layout](#3-application-shell--main-layout)
4. [Design System](#4-design-system)
5. [Navigation System](#5-navigation-system)
6. [Global Search & Quick Actions](#6-global-search--quick-actions)
7. [Login & Session Screens](#7-login--session-screens)
8. [Dashboard](#8-dashboard)
9. [Module Screen Catalog](#9-module-screen-catalog)
10. [Dialog Catalog](#10-dialog-catalog)
11. [Workflow Catalog](#11-workflow-catalog)
12. [Notifications](#12-notifications)
13. [Keyboard Shortcuts & Productivity](#13-keyboard-shortcuts--productivity)
14. [Accessibility](#14-accessibility)
15. [Responsive & Multi-Monitor](#15-responsive--multi-monitor)
16. [Cross-Platform Adaptation](#16-cross-platform-adaptation)
17. [Screen Spec Template (Mandatory)](#17-screen-spec-template-mandatory)
18. [Compliance](#18-compliance)

---

## 1. Product Vision & UX Principles

### 1.1 Product promise

SMOXI Service is an **international service-management ERP** for repair shops, field service, and multi-branch operations. The desktop app is the primary workstation; Web and mobile reuse the same navigation model and visual language.

### 1.2 UX principles

| Principle | Meaning in SMOXI |
|-----------|------------------|
| **Minimum clicks** | Common tasks ≤ 3 clicks from Dashboard |
| **Scan, then act** | Lists + filters first; details on demand |
| **Never block** | Heavy work off UI thread; clear progress |
| **One job per screen** | Each page has a single primary purpose |
| **Recoverable** | Confirm destructive actions; Undo where safe |
| **Local-first clarity** | Offline-capable desktop; sync status always visible |
| **International** | Every string localizable; RTL-ready layouts later |

### 1.3 Interaction goals

- Reception creates a work order in under **60 seconds** with keyboard.
- Technicians update status without hunting menus.
- Managers see today’s health on Dashboard without opening reports.
- Admins configure once; operators never see admin clutter.

---

## 2. Information Architecture

### 2.1 Top-level domains (sidebar)

| # | Domain | Route id | Primary users |
|---|--------|----------|---------------|
| 1 | Dashboard | `dashboard` | All |
| 2 | Customers | `customers` | Reception, Sales, Managers |
| 3 | Companies | `companies` | B2B, Managers |
| 4 | Reception | `reception` | Front desk |
| 5 | Work Orders | `work_orders` | Reception, Techs, Managers |
| 6 | Technicians | `technicians` | Managers, Dispatch |
| 7 | Inventory | `inventory` | Warehouse, Purchasing |
| 8 | Warehouse | `warehouse` | Warehouse |
| 9 | Suppliers | `suppliers` | Purchasing |
| 10 | Finance | `finance` | Finance, Managers |
| 11 | Invoices | `invoices` | Finance, Reception |
| 12 | Payments | `payments` | Finance, Cashier |
| 13 | Reports | `reports` | Managers, Finance |
| 14 | Calendar | `calendar` | All operational |
| 15 | Notifications | `notifications` | All |
| 16 | Telegram | `telegram` | Admins, Ops |
| 17 | Automation | `automation` | Admins |
| 18 | AI Assistant | `ai_assistant` | Licensed users |
| 19 | Settings | `settings` | Admins, Managers |
| 20 | Administration | `administration` | System admins |
| 21 | Help | `help` | All |
| 22 | About | `about` | All |
| — | Logout | `logout` | All (action, not page) |

### 2.2 Navigation depth

```text
Shell
 └─ Domain (sidebar)
     └─ Section / List
         └─ Detail (tabs)
             └─ Dialog / Drawer (modal or side)
```

Maximum recommended depth before a dialog: **3**.

---

## 3. Application Shell & Main Layout

### 3.1 Shell regions

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ TOP BAR  [Logo] [Global Search] [Quick Actions] [Theme] [Lang] [User] [🔔]│
├────────────┬─────────────────────────────────────────────────────────────┤
│            │ WORKSPACE HEADER  Breadcrumb · Title · Page Actions         │
│  LEFT      ├─────────────────────────────────────────────────────────────┤
│  SIDEBAR   │                                                             │
│  (nav +    │              WORKSPACE (pages / tabs / splits)              │
│   pins)    │                                                             │
│            │                                                             │
├────────────┴─────────────────────────────────────────────────────────────┤
│ STATUS BAR  Sync · DB · User · Branch · License · Clock · Zoom           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Top Bar — components

| Component | Purpose | Actions |
|-----------|---------|---------|
| **Brand / Logo** | Product identity; click → Dashboard | Navigate home |
| **Global Search** | Search everywhere (`Ctrl+K`) | Open command palette |
| **Quick Actions** | New WO, New Customer, Receive Payment | Open create flows |
| **Recent Activities** flyout | Last 20 user actions | Jump to entity |
| **Theme toggle** | Light / Dark | Persist per user |
| **Language selector** | Locale switch | Reload UI strings |
| **Notification bell** | Unread badge | Open Notification Center |
| **User menu** | Profile, Preferences, Lock, Logout | Account actions |

**User menu items:** My Profile · Preferences · Keyboard Shortcuts · Lock Screen · Switch Branch (if multi-branch) · Logout

### 3.3 Left Sidebar

| Element | Behavior |
|---------|----------|
| Collapse / expand | `Ctrl+B`; icons-only when collapsed |
| Sections | Operational · Commerce · Insights · System |
| Active item | Strong indicator + aria-current |
| Favorites / Pins | User-pinned routes above fold |
| Recent pages | Last 8 distinct pages |
| Badge counts | WO waiting, low stock, unread notifications |

**Sidebar order** (exact product menu):

1. Dashboard
2. Customers
3. Companies
4. Reception
5. Work Orders
6. Technicians
7. Inventory
8. Warehouse
9. Suppliers
10. Finance
11. Invoices
12. Payments
13. Reports
14. Calendar
15. Notifications
16. Telegram
17. Automation
18. AI Assistant
19. Settings
20. Administration
21. Help
22. About
23. Logout

### 3.4 Workspace

- Hosts the active page; supports **tabbed documents** (optional user preference: single page vs multi-tab).
- Default: **single primary page** + optional **right inspector** (320–400px) for AI Assistant / entity summary.
- Empty workspace shows welcome + Quick Shortcuts.

### 3.5 Status Bar

| Segment | Content |
|---------|---------|
| Left | Connection: Local DB · Sync status (`Synced` / `Pending` / `Offline`) |
| Center | Active branch / warehouse · Environment badge (Dev/Staging only) |
| Right | License status · App version · Local time · UI scale % |

### 3.6 Notification Area

- Top-bar bell + optional system tray.
- Toast stack: bottom-right, max 3 visible, queue.
- Notification Center: full list with filters (see §12).

---

## 4. Design System

### 4.1 Visual direction

**Enterprise service workstation** — calm slate surfaces, precise typography, amber action accent (repair/energy), teal success for completed jobs.
Avoid: purple-gradient SaaS clichés, cream+terracotta “AI brochure,” newspaper layouts.

### 4.2 Color tokens

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-bg-app` | `#F4F6F8` | `#0F1419` | App background |
| `--color-bg-surface` | `#FFFFFF` | `#1A222C` | Cards, panels |
| `--color-bg-sidebar` | `#E8EEF3` | `#121820` | Sidebar |
| `--color-border` | `#D0D7DE` | `#2A3440` | Dividers |
| `--color-text-primary` | `#14202B` | `#E8EEF3` | Body |
| `--color-text-secondary` | `#5B6B7C` | `#9AA8B5` | Meta |
| `--color-primary` | `#1F4E79` | `#5B9BD5` | Brand, primary buttons |
| `--color-secondary` | `#3D5A40` | `#7FA187` | Secondary emphasis |
| `--color-accent` | `#C47A12` | `#E0A04A` | Quick actions, highlights |
| `--color-success` | `#1F7A4D` | `#3CB371` | Success, completed |
| `--color-warning` | `#B86E00` | `#F0A202` | Warnings, waiting |
| `--color-danger` | `#B42318` | `#F04438` | Errors, delete |
| `--color-info` | `#175CD3` | `#53B1FD` | Info banners |

**Status chips (work orders):** Draft · Received · Diagnosing · Waiting Parts · In Repair · QA · Ready · Delivered · Cancelled — each mapped to token + icon.

### 4.3 Typography

| Role | Font | Size (desktop base) | Weight |
|------|------|---------------------|--------|
| Display / brand | **IBM Plex Sans** | 28–32 | 600 |
| Page title | IBM Plex Sans | 22 | 600 |
| Section | IBM Plex Sans | 16 | 600 |
| Body | IBM Plex Sans | 14 | 400 |
| Table / dense | IBM Plex Sans | 13 | 400 |
| Mono (IDs, barcodes) | **IBM Plex Mono** | 12–13 | 500 |

Minimum readable body: 13px. Large-font mode: scale +12.5% / +25%.

### 4.4 Spacing & layout grid

| Token | Value |
|-------|-------|
| `--space-1` … `--space-8` | 4, 8, 12, 16, 24, 32, 48, 64 px |
| Page padding | 24 px |
| Card padding | 16–20 px |
| Form row gap | 12–16 px |
| Table row height | 40 px (comfortable) / 32 px (compact) |
| Sidebar width | 248 px expanded / 64 px collapsed |

### 4.5 Icons

- Style: outlined 20×20 (sidebar 22×22), 1.75 stroke.
- Library: consistent set (Phosphor / Lucide-equivalent); **one family only**.
- Never mix filled and outlined arbitrarily; filled = selected/active only.

### 4.6 Buttons

| Type | Use | Style |
|------|-----|-------|
| Primary | Main CTA | Filled primary |
| Secondary | Alternate | Outline |
| Tertiary / Ghost | Low emphasis | Text |
| Danger | Destructive | Filled danger |
| Icon button | Toolbars | 32×32 hit area |

States: default · hover · pressed · focus-visible · disabled · loading.

### 4.7 Cards

Allowed for **interactive containers** and dashboard widgets only.
Not for decorative wrapping of every section. Prefer flat sections with clear headings.

### 4.8 Tables

Mandatory features: column resize, column visibility, sort, multi-filter, density toggle, sticky header, row selection, context menu, export from toolbar, empty/error/skeleton states.

### 4.9 Forms

- Labels above fields; required marker `*`.
- Inline validation on blur; summary on submit.
- Field help as subtle caption, not modal.
- Dangerous fields (delete reason) require explicit confirmation dialog.

### 4.10 Motion

| Motion | Duration | Use |
|--------|----------|-----|
| Page fade/slide | 150–200 ms | Route change |
| Drawer | 200 ms | Inspectors |
| Toast | 200 ms in / auto out | Feedback |
| Skeleton shimmer | Continuous | Loading |

Reduce motion: honor OS “prefer reduced motion”.

### 4.11 Feedback states

| State | Pattern |
|-------|---------|
| Loading | Skeleton for lists/cards; spinner for buttons |
| Empty | Illustration + one sentence + primary CTA |
| Error | Banner + retry; log correlation id in detail |
| Success | Toast or inline banner; no modal unless print/payment |

---

## 5. Navigation System

### 5.1 Mechanisms

| Mechanism | Trigger |
|-----------|---------|
| Sidebar | Click / keyboard |
| Breadcrumbs | Click ancestor |
| Global Search / Command palette | `Ctrl+K` |
| Quick Actions | Top bar / `Ctrl+N` menu |
| Tabs (optional) | Open entity in new tab |
| Deep links | `smoxi://work_orders/{uuid}` (future) |
| Back/Forward | `Alt+←` / `Alt+→` |

### 5.2 Permission gating

- Sidebar items **hidden** if user lacks `module.view`.
- Buttons **disabled + tooltip** if action lacks permission (prefer hide for create/delete in constrained roles).
- Attempting deep navigation without permission → friendly access-denied page.

### 5.3 Favorites, Recents, Pins

| Feature | Behavior |
|---------|----------|
| Favorites | Star on page header; listed under sidebar “Favorites” |
| Recent pages | Auto; last 8 |
| Pinned pages | Drag reorder; persist per user |

---

## 6. Global Search & Quick Actions

### 6.1 Global Search (Command Palette)

**Purpose:** Find entities and run commands without leaving keyboard.

**Components:** Search input · Result groups · Keyboard hints · Recent queries

**Result groups (in order):** Commands · Work Orders · Customers · Devices · Invoices · Inventory · Technicians · Pages

**Actions:** Enter opens · `Ctrl+Enter` opens in new tab · Esc closes

**Permissions:** Results filtered by user rights

**Validation:** Debounced ≥ 200 ms; min 2 characters (except commands)

**Related:** All entity detail pages

**Future:** Natural language (“overdue Samsung screens”) via AI Assistant

### 6.2 Domain searches

| Search | Entry points | Fields indexed (UX) |
|--------|--------------|---------------------|
| Customer | Customers list, Reception, Global | Name, phone, email, code |
| Device | Customer detail, Reception, Global | Serial, IMEI, brand/model |
| Invoice | Invoices, Finance, Global | Number, customer, amount |
| Work Order | WO list, Reception, Global | WO#, customer, device, status |
| Technician | Technicians, Assignment dialog | Name, skill, status |
| Inventory | Inventory, WO parts | SKU, barcode, name |
| QR Search | `Ctrl+Shift+Q` / scanner | Decode → entity |
| Barcode Search | Scanner wedge / `Ctrl+Shift+B` | Barcode → item/WO |

### 6.3 Quick Actions menu

Default items (permission-filtered):

1. New Work Order
2. New Customer
3. Receive Device (Reception)
4. Take Payment
5. Create Invoice
6. Stock Adjustment
7. Open AI Assistant
8. Backup Now (admin)

---

## 7. Login & Session Screens

### 7.1 Login Screen

| Field | Spec |
|-------|------|
| **Purpose** | Authenticate user and establish session |
| **Components** | Company logo · Company selector/field · Username · Password · Remember Me · Language · Theme · License status badge · Version label · Environment badge (non-prod) |
| **Buttons** | **Login** (primary) · **Exit** · **Forgot Password** (link) |
| **Menus** | Language · Theme (Light/Dark/System) |
| **Actions** | Validate → authenticate → load shell; Exit confirms if offline changes pending |
| **Navigation** | Success → Dashboard (or last page if Remember + preference) · Forgot Password → Password Recovery |
| **Permissions** | Public (pre-auth) |
| **Validation** | Required company/user/password; lockout message after N failures (no user enumeration) |
| **Related Screens** | Password Recovery · License Expired · Lock Screen |
| **Future** | SSO / Windows Hello / QR desk login |

### 7.2 Password Recovery

Purpose: request reset via email/admin. Components: identifier field, Submit, Back to Login. No security answers in UI that leak policy.

### 7.3 Lock Screen

Purpose: secure workstation without full logout. Shows avatar, Unlock, Switch User, Logout.

### 7.4 License Expired / Invalid

Purpose: block operational modules; allow Settings→License and Exit. Clear renewal CTA.

---

## 8. Dashboard

### 8.1 Dashboard Home

| Spec | Detail |
|------|--------|
| **Purpose** | At-a-glance operations, finance pulse, and shortcuts for the current day/branch |
| **Components** | KPI row · Charts · Lists · Shortcuts · Notifications snippet · AI Assistant panel (collapsible) |
| **Buttons** | Refresh · Customize Layout · Date Range · Branch filter |
| **Menus** | Widget visibility · Export dashboard PDF |
| **Actions** | Click KPI → filtered list; Click activity → entity |
| **Navigation** | To WO/Customers/Finance/Inventory as deep links |
| **Permissions** | `dashboard.view`; widgets filtered by role |
| **Validation** | Date range max 1 year |
| **Related** | All operational modules |
| **Future** | Per-role saved layouts; AI narrative summary |

### 8.2 Dashboard widgets (mandatory catalog)

| Widget | Content | Click-through |
|--------|---------|---------------|
| Today’s Repairs | Count in-progress today | WO list filtered |
| Waiting Repairs | Waiting parts / customer | WO list |
| Completed Repairs | Completed today | WO list |
| Revenue | Today / MTD toggle | Finance dashboard |
| Expenses | Today / MTD | Expenses |
| Profit | Computed MTD | Financial reports |
| Customers | New + active counts | Customers |
| Technicians | Available / busy | Technicians board |
| Inventory Alerts | Below minimum | Inventory low-stock |
| Recent Activities | Feed | Activity detail / entity |
| Monthly Statistics | Chart | Reports |
| Charts | Status mix, revenue trend | Reports |
| Quick Shortcuts | Icon grid | Target pages |
| Notifications | Latest unread | Notification Center |
| AI Assistant Panel | Suggestions / ask | Expand AI |

---

## 9. Module Screen Catalog

> Each screen below follows the mandatory template (§17). Buttons listed are **required** unless marked optional.

### 9.1 Customers

#### Customer List

| Spec | Detail |
|------|--------|
| **Purpose** | Find and manage customers |
| **Components** | Filter bar · Data table · Bulk action bar · Export |
| **Buttons** | New Customer · Import · Export · Refresh · Columns |
| **Menus** | Row context: Open · Edit · New WO · New Invoice · Deactivate · Merge (admin) |
| **Actions** | Double-click → Details; Delete = soft deactivate via dialog |
| **Navigation** | → Customer Details; ← Dashboard |
| **Permissions** | `customers.view` / `.create` / `.edit` / `.delete` |
| **Validation** | Filters sane ranges; search min 2 chars |
| **Related** | Companies, Reception, Work Orders, Invoices |
| **Future** | Map view, duplicate detection assistant |

#### Customer Details (tabbed)

**Tabs:** Overview · Repair History · Invoices · Warranty · Payments · Devices · Notes · Attachments · Communication History

| Spec | Detail |
|------|--------|
| **Purpose** | 360° customer record |
| **Components** | Header (name, phones, tags, balance) · Tabs · Side activity |
| **Buttons** | Edit · New Work Order · New Invoice · Take Payment · More |
| **Menus** | Print statement · Merge · GDPR export (admin) |
| **Actions** | Save validates; Auto-save drafts for Notes |
| **Navigation** | To WO/Invoice/Device details |
| **Permissions** | Tab-level permissions |
| **Validation** | Phone/email formats; required display name |
| **Related** | All commerce modules |
| **Future** | Timeline unified view |

*(Sub-tabs are pages-within-page; each supports empty/error states and own toolbars.)*

### 9.2 Companies

#### Company List / Company Details

Mirror Customer patterns with B2B fields: VAT/Tax ID, credit limit, contacts, linked customers, contracts.
Buttons: New Company · Add Contact · Link Customer · Credit Hold.

### 9.3 Reception

#### Reception Desk

| Spec | Detail |
|------|--------|
| **Purpose** | Fast intake of devices and creation of work orders |
| **Components** | Full-width intake card · stacked field labels · Phone/Name/Device/Problem/Price · Collapsible Additional (brand, serial, accessories, work scope, parts) · Footer totals + Clear/Accept · Info tip |
| **Buttons** | Create Work Order · Clear · Add/Edit/Remove part (in Additional) |
| **Menus** | Templates for common faults (future) |
| **Actions** | Create WO → stay for next intake; QR bot link if customer not linked |
| **Navigation** | Customers · Work Orders · Inventory (parts at desk) |
| **Permissions** | `reception.use`, `work_orders.create` |
| **Validation** | Phone + device model + problem required (`*` marks); brand/serial/accessories optional |
| **Related** | Customer Details, Work Order List |
| **Future** | Kiosk mode; label printer; fault templates; category-specific identity fields |
| **Visual** | Design tokens: slate card, primary border `#1F4E79`, amber Accept, light/dark; card spans workspace (not a narrow centered column) |

### 9.4 Work Orders

#### Work Order List

Filters: status, technician, date, priority, branch.
Toolbar: Search · Status filter · Branch · Refresh.
**Row context menu (right-click):** Change Status · Quick Repairing / Waiting Parts / Ready · Deliver · Assign · Timeline/QR · CX panel · Cancel · Delete.
**Hotkeys (selected row):** `F5` Refresh · `F6` Status · `F7` Repairing · `F8` Parts · `F9` Ready · `F10` Deliver · `F11` Assign · `F12` Timeline/QR · `Delete` Cancel · `Ctrl+Delete` Soft-delete.
Double-click row → Change Status.
View modes: **Table** | **Kanban** | **Calendar** (Kanban/Calendar — future).

#### New / Edit Work Order

Sections: Customer · Device · Intake · Diagnosis · Parts · Labor · Costs · Schedule · Documents.
Buttons: Save Draft · Submit · Assign Technician · Add Part · Add Labor · Attach File · Cancel.

#### Work Order Details

| Spec | Detail |
|------|--------|
| **Purpose** | Operate a single repair job end-to-end |
| **Components** | Status header · Repair Timeline · Status Timeline · Photos · Files · Parts/Labor grids · Cost summary · Notes |
| **Buttons** | Change Status · Assign · Request Approval · Mark Ready · Deliver · Print · More |
| **Menus** | Warranty · Refund request · Duplicate WO · Reopen |
| **Dialogs** | Approval · Delivery · Warranty · Payment (if COD) · **CX Timeline/QR** (`CxTimelineDialog`) · **CX panel** (`CxHubDialog`) |
| **Navigation** | Customer · Technician · Invoice · Inventory movements |
| **Permissions** | Status transitions matrix by role |
| **Validation** | Illegal status jumps blocked with reason |
| **Related** | All operational modules · [CustomerExperienceModule.md](CustomerExperienceModule.md) CX-A…H |
| **Future** | Live tech tracking; customer portal mirror |

**Required subviews:** Repair Timeline · Status Timeline · Photos · Files · Technician Assignment panel · Repair Cost · Repair Notes.

**CX-A (2026-07-24):** List page **Timeline / QR** button opens `CxTimelineDialog` — append-only `work_order_timeline_events` + `public_token` QR payload `SMOXI|code|WO-number|token`.

**CX-B…H (2026-07-24 / 1.5.0):** List page **CX panel** — intake media/imzo/PDF, smeta yuborish, admin istisnosi; Reception CX maydonlari; Reports texnik KPI; ombor rezerv/deduct + kafolat on DELIVERED.

### 9.5 Technicians

#### Technician List / Board / Details

Board: Available · Busy · On Leave.
Details tabs: Profile · Skills · Schedule · Open Jobs · Performance · Documents.
Buttons: Assign Job · Set Availability · Message (Telegram).

### 9.6 Inventory

| Screen | Purpose | Key buttons |
|--------|---------|-------------|
| Items List | Catalog & stock levels | New Item · Adjust · Print Labels |
| Item Details | Master + stock by warehouse | Edit · Movements · Suppliers |
| Categories | Tree of categories | Add · Reorder · Merge |
| Suppliers (link) | Jump/filter to suppliers | Open Supplier |
| Purchase Orders | PO list/detail | New PO · Receive · Cancel |
| Stock Movement | History of in/out/adjust | Filter · Export |
| Minimum Stock | Reorder rules | Edit Thresholds · Create PO suggestions |
| Barcode / QR tools | Generate & print | Print · Download |
| Warehouse Transfer | Move between warehouses | Create Transfer · Ship · Receive |
| Inventory History | Audit trail | Export |

### 9.7 Warehouse

Warehouse List · Bin Locations · Transfer Desk · Receiving · Picking (future).
Buttons: New Warehouse · Transfer · Cycle Count.

### 9.8 Suppliers

Supplier List · Details (contacts, POs, items, payments, notes).
Buttons: New · New PO · Record Bill.

### 9.9 Finance

| Screen | Purpose |
|--------|---------|
| Financial Dashboard | Cash, AR, AP, profit widgets |
| Invoices (module alias) | See §9.10 |
| Payments | See §9.11 |
| Cash Register | Sessions open/close, cash movements |
| Expenses | Expense list/detail, categories |
| Profit | P&L summary views |
| Taxes | Tax rates, reports links |
| Refunds | Refund queue & detail |

### 9.10 Invoices

Invoice List · Invoice Detail · New Invoice (from WO or manual).
Buttons: New · Issue · Send · Print · Record Payment · Credit Note · Void.
Validation: line items, tax, customer required; void needs reason.

### 9.11 Payments

Payment List · Take Payment dialog/page · Allocation to invoices.
Buttons: Take Payment · Refund · Print Receipt · Reconcile.

### 9.12 Reports

| Report | Purpose |
|--------|---------|
| Daily / Weekly / Monthly / Yearly | Operational & financial summaries |
| Technician Performance | Jobs, time, CSAT proxies |
| Customer Statistics | Cohort, revenue, returns |
| Inventory Reports | Valuation, movement, dead stock |
| Financial Reports | P&L, cash, taxes |
| Charts Gallery | Saved chart views |

**Common chrome:** Date range · Branch · Filters · **Run** · **PDF Export** · **Excel Export** · **Print Preview** · Schedule (future).

### 9.13 Calendar

Views: Day · Week · Month · Agenda.
Entities: WO appointments, tech shifts, reminders.
Actions: Drag to reschedule · Create event · Link WO.

### 9.14 Notifications

Notification Center page (full). Filters: All · Unread · Mentions · System · Sync.
Actions: Mark read · Open entity · Mute type · Preferences link.

### 9.15 Telegram

| Spec | Detail |
|------|--------|
| **Purpose** | Bot holati, mijoz suhbatlari (kiruvchi/chiquvchi), javob yuborish |
| **Components** | Connection status · Thread list · Message pane · Reply box · Refresh |
| **Buttons** | Yangilash · Yuborish |
| **Actions** | Suhbatni ochish · Oʻqilgan deb belgilash · Javob yuborish |
| **Navigation** | Sidebar `telegram`; Sozlamalar → bot token |
| **Permissions** | `telegram.admin` (MVP: authenticated ops) |
| **Validation** | Token majburiy; boʻsh javob taqiqlangan |
| **Related** | Work Orders (status notify), Reception (quote), Settings |
| **Future** | Message templates · Delivery log · Test message |

### 9.16 Automation

Rule list · Rule builder · Run history.
Actions: Enable/Disable · Test · Duplicate.

### 9.17 AI Assistant

| Spec | Detail |
|------|--------|
| **Purpose** | Assist operators with search, summaries, suggested next steps |
| **Components** | Chat panel · Context chips (current page entity) · Suggestions · History |
| **Buttons** | Send · Clear · Insert into Notes · Create Task |
| **Permissions** | `ai.use`; respects data permissions |
| **Validation** | Rate limits; no silent destructive actions |
| **Related** | Any entity page via context |
| **Future** | Voice; auto diagnosis drafts |

### 9.18 Settings

| Screen | Purpose | Key actions |
|--------|---------|-------------|
| Company | Legal name, address, logo, branches | Save |
| Users | User list/detail | Invite · Disable |
| Permissions | Roles & matrix | Edit role · Clone |
| Localization | Language, region, formats | Save |
| Currencies | Multi-currency | Add · Rates |
| Tax | Tax codes | Add · Default |
| Telegram | Bot tokens (masked) | Test · Save |
| Backup | Create backup | Backup Now · Schedule |
| Restore | Restore from file | Restore (danger) |
| Updates | Check/install updates | Check · Install |
| License | Key, seats, expiry | Activate |
| Appearance | Theme, density, fonts | Preview · Save |
| Notifications | Channels & quiet hours | Save |
| Database | Backend info, maintenance | Vacuum (dev) · Migrate |
| Security | Password policy, sessions, 2FA | Save · Revoke sessions |

### 9.19 Administration

System health · Audit log · Job queue · Feature flags · Danger zone (reset demos — disabled in prod).
Permissions: `admin.*` only.

### 9.20 Help / About

**Help:** Searchable topics, shortcuts cheat-sheet, contact support.
**About:** Product name, version, license summary, third-party notices, Update check.

---

## 10. Dialog Catalog

Every dialog: title · body · primary/secondary actions · Esc closes (if safe) · focus trap · localized.

| Dialog | Purpose | Primary / Secondary | Notes |
|--------|---------|---------------------|-------|
| Confirmation | Generic yes/no | Confirm / Cancel | |
| Delete (Soft) | Confirm soft delete | Delete / Cancel | Show entity name; optional reason |
| Save Conflicts | Dirty form leave | Save · Discard · Cancel | |
| Exit Application | Quit app | Exit / Cancel | Warn unsaved + pending sync |
| Warning | Blocking caution | OK / Cancel | |
| Success | Rare modal success | OK | Prefer toast |
| Error | Blocking error | OK · Retry · Details | Details → log id |
| Information | Neutral notice | OK | |
| Print | Print options | Print / Cancel | Printer, copies |
| Export | Format & range | Export / Cancel | PDF/Excel/CSV |
| Import | File + mapping | Import / Cancel | Preview rows |
| Customer Approval | Customer accepts estimate | Approve / Reject / Request Changes | Signature optional |
| Repair Completion | Tech marks done | Complete / Cancel | Checklist |
| Delivery | Handover device | Deliver / Cancel | ID check, signature, payment status |
| Payment | Collect payment | Charge / Cancel | Method, amount, change |
| Warranty | Register/claim warranty | Save / Cancel | Terms display |
| Assign Technician | Pick tech | Assign / Cancel | Skill/workload hints |
| Status Change | Transition WO | Apply / Cancel | Required comment on some states |
| License Activation | Enter key | Activate / Cancel | |
| Backup Confirm | Start backup | Start / Cancel | |
| Restore Confirm | Destructive restore | Restore / Cancel | Typed CONFIRM |

---

## 11. Workflow Catalog

### 11.1 Device intake → delivery (happy path)

```text
Login → Reception Desk → Find/Create Customer → Capture Device
  → Create Work Order → (optional) Estimate Approval Dialog
  → Assign Technician → In Repair (timeline updates, parts, photos)
  → QA / Ready → Invoice → Payment Dialog → Delivery Dialog
  → Warranty Dialog (optional) → Dashboard/List
```

### 11.2 Parts shortage

```text
WO Details → Add Part (insufficient stock) → Warning
  → Create PO suggestion → PO → Receive Stock → Resume WO
```

### 11.3 Payment only

```text
Invoices/Payments → Take Payment → Allocate → Receipt Print → Done
```

### 11.4 End of day

```text
Cash Register → Close Session → Variance Warning? → Report Print → Backup (optional)
```

### 11.5 Undo / Redo / Auto Save

| Feature | Scope |
|---------|-------|
| Auto Save | Forms with drafts (Notes, long WO descriptions) every 30s when dirty |
| Undo/Redo | Text editors; limited structural undo for Kanban moves in-session |
| Discard | Explicit via Save Conflicts dialog |

---

## 12. Notifications

| Channel | When | User control |
|---------|------|--------------|
| Desktop toast | In-app events | On/off per category |
| OS / tray | Background sync, long jobs | OS permission |
| Telegram | WO ready, critical alerts | Opt-in + templates |
| Email | Invoices, digests | Opt-in |
| Sound | Optional on toast | Mute / volume |
| Status badge | Sidebar & bell counts | Always on if permitted |

**Notification Center:** list, filters, mark read, open target, preferences link.

**Severity:** info · success · warning · error (maps to design tokens).

---

## 13. Keyboard Shortcuts & Productivity

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Global Search |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+N` | Quick Actions / New menu |
| `Ctrl+S` | Save current form |
| `Ctrl+F` | Focus list filter / in-page find |
| `Ctrl+P` | Print |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Ctrl+Shift+Q` | QR Search |
| `Ctrl+Shift+B` | Barcode Search |
| `F5` | Refresh current view |
| `Esc` | Close dialog / clear selection |
| `Alt+←` / `Alt+→` | Navigate history |
| `?` | Shortcuts help (when not in input) |

**Work Orders page (selected row):**

| Shortcut | Action |
|----------|--------|
| `F5` | Refresh list |
| `F6` | Change status |
| `F7` | Quick → Repairing |
| `F8` | Quick → Waiting parts |
| `F9` | Mark Ready |
| `F10` | Deliver to customer |
| `F11` | Assign technician |
| `F12` | Timeline / QR |
| `Delete` | Cancel work order |
| `Ctrl+Delete` | Soft-delete work order |

**Context menus:** on all tables and timeline items — Open, Edit, Copy ID, relevant actions.

**Drag and drop:** Kanban status moves · Calendar reschedule · Attachment drop zones · Sidebar pin reorder.

---

## 14. Accessibility

| Requirement | Spec |
|-------------|------|
| Keyboard | All actions reachable; visible focus rings |
| High contrast | Theme variant + OS high contrast respect |
| Scaling | 100 / 125 / 150 / 200% UI scale |
| Large fonts | Appearance setting |
| Color blind | Status never color-only; icons + text |
| Screen readers | Accessible names on controls (Qt a11y) |
| Motion | Respect reduced motion |

---

## 15. Responsive & Multi-Monitor

| Target | Layout behavior |
|--------|-----------------|
| Full HD 1920×1080 | Default reference |
| 2K / 4K | Scale tokens; denser optional |
| Height < 800 | Compact density default suggestion |
| Multi-monitor | Optional detachable WO Details / Reports windows |
| Min supported | 1366×768 with collapsed sidebar |

Workspace panels: collapsible AI inspector; remember sizes per monitor configuration.

---

## 16. Cross-Platform Adaptation

| Platform | Adaptation |
|----------|------------|
| Windows Desktop | Full shell; primary |
| Web | Same IA; top bar + collapsible nav; no OS tray |
| Android / iOS | Bottom nav for core 5 (Dashboard, WO, Reception, Inventory, More); dialogs → full-screen sheets |

Shared: design tokens, status colors, terminology, permission model.

---

## 17. Screen Spec Template (Mandatory)

Every new screen PR **must** document:

```markdown
### <Screen Name>

| Spec | Detail |
|------|--------|
| Purpose | |
| Components | |
| Buttons | |
| Menus | |
| Actions | |
| Navigation | |
| Permissions | |
| Validation | |
| Related Screens | |
| Future Improvements | |
```

---

## 18. Compliance

| Role | Duty |
|------|------|
| Designer / Product | Update this blueprint before net-new screens ship |
| Developer / AI | Implement only screens defined here (or extend this doc in the same PR) |
| Reviewer | Reject UI that violates shell, tokens, or navigation rules |

**Document changes** require PR `docs(ui): …` and a ChangeLog entry.

---

## Appendix A — Permission Naming (UI)

Pattern: `<module>.<action>`

Examples: `work_orders.view`, `work_orders.create`, `work_orders.assign`, `work_orders.deliver`, `inventory.adjust`, `finance.refund`, `settings.users`, `admin.audit`.

---

## Appendix B — Empty / Error Copy Tone

- Empty: “No work orders match these filters.” + Clear filters CTA
- Error: “We couldn’t load work orders. Try again.” + Retry
- Never: stack traces, SQL, raw exception types

---

## Document History

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-07-23 | Initial official UI/UX Blueprint (Phase 3) |

---

*End of SMOXI Service Enterprise UI/UX Blueprint*
