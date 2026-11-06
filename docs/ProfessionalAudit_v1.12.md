# SMOXI Service ERP — Professional Audit Report

**Product:** SMOXI SERVICE ERP
**Version audited:** 1.12.0
**Scope:** Desktop (PySide6), FastAPI, SQLite, Telegram Bot + Staff/Customer Mini Apps
**Scale:** ~395 Python files (excl. venv), 29 feature modules, 30 test modules
**Overall score:** **58 / 100** — commercial **MVP+** / early ERP; not yet Microsoft Fluent / Linear / Odoo enterprise bar

> **Progress (v1.13.0):** P1 hardening started — default secret mint/block, force admin password change, bot token at-rest encryption, toast UX, Payments page, Customer 360 tabs, Mini App stock sheet, named Cloudflare tunnel support, Alembic scaffold. Re-audit recommended after remaining list pagination + full migration cutover.

**Interactive summary:** open the Cursor canvas `smoxi-erp-audit.canvas.tsx` beside chat.

> Methodology note: Inventing filler to force exactly “100” items per category would dilute signal. Each list below is **ranked by severity/value** with as many **evidence-backed** findings as the codebase supports. Prefer fixing P1 items over chasing list length.

---

## 0. Executive verdict

| Dimension | Score /10 | One line |
|-----------|----------:|----------|
| Architecture | 7.2 | Clean modular monolith; controllers unused |
| UI | 5.8 | Solid QSS tokens; hardcoded dark-mode breaks |
| UX | 5.5 | Ops flows work; toast/shell chrome incomplete |
| Security | 4.8 | Defaults + plaintext bot token = blockers |
| Performance | 5.2 | Fine for SMB; not ready for 1M rows |
| Business Logic | 7.0 | Reception→WO→stock→pay→Telegram real |
| Scalability | 4.5 | SQLite + patches; single-node |
| Database | 5.0 | Soft-delete OK; no Alembic |
| Code Quality | 6.4 | Typed services; empty scaffolds |
| Testing | 4.2 | Service tests; almost no UI E2E |
| ERP Completeness | 6.8 | Service-center ERP; no GL/approvals |
| **Overall** | **58/100** | Sellable after P1 hardening |

---

## 1. Project architecture

### What works
- Package split: `ui → services → repositories → models`
- `ServiceContainer` composition root
- Soft-delete `AuditMixin` (`uuid`, `version`, `sync_status`, …)
- Module READMEs for many domains
- Binding docs: EngineeringStandards, UIUXBlueprint, BA, Master Prompt

### Findings (ranked)

| # | Muammo | Sababi | Risk | Yechim | Priority |
|---|--------|--------|------|--------|----------|
| 1 | Controllers empty; views call services | Layer declared but unused | Maintainability | Thin use-case/controller layer | P2 |
| 2 | No Alembic; `schema_patches.py` | Fast iteration debt | Data loss on upgrade | Alembic for SQLite+Postgres | P1 |
| 3 | Empty modules: invoices, payments, assets | Blueprint ahead of code | IA confusion | Implement or remove packages | P1 |
| 4 | MainWindow imports all pages | Tight coupling | Startup cost | Lazy page factory | P2 |
| 5 | `app.models` eager import graph | Circular risk | Import cycles | Lazy model registry | P3 |
| 6 | Dual “companies” naming | Tenant vs B2B | UX confusion | Rename routes/labels | P2 |
| 7 | warehouse UI vs inventory.warehouse | Split ownership | Drift | Single stock domain API | P3 |
| 8 | Plugins registry placeholder | Roadmap checkbox | False completeness | Real hook points or defer | P4 |
| 9 | Root `app/schemas` empty | Inconsistent schema home | Drift | Module schemas only OR central | P3 |
| 10 | Placeholder page leftover | Dead code | Noise | Delete | P3 |
| 11 | Stale module `__init__` strings | Doc drift | Confusion | Sync package docs | P3 |
| 12 | Two FastAPI apps + desktop | OK but ops complex | Ops | Document ports 8765/8787 | P2 |
| 13 | CX README Feature 13 outdated | Docs lag | Wrong planning | Update README | P3 |
| 14 | Database.md placeholder | Standards gap | Onboarding | Write real ERD | P2 |
| 15 | BA permission names ≠ code | `customers.create` vs `manage` | Auth bugs | Align matrices | P1 |
| 16 | No DI lifetime scopes | New service per call | OK small; unclear at scale | Document pattern | P3 |
| 17 | Sync + Mini App share container | Threading care | Race | Session-per-request discipline | P2 |
| 18 | Missing READMEs (settings, users, …) | Incomplete module delivery | Onboarding | Add per EngineeringStandards | P3 |

---

## 2. UI / UX audit

### Shell vs UIUXBlueprint
Present: Top bar, sidebar, workspace, status, toast, Ctrl+K, light/dark.
Missing: Quick Actions, User menu, language selector, sidebar collapse, status clock/license/zoom.

### Ranked UI issues
1. Brand label hardcoded `#0F2D4A` — dark mode wrong
2. Toast top-right vs blueprint bottom-right stack
3. Toast ignores dark theme (hardcoded primary)
4. Success via `QMessageBox` everywhere
5. No language switcher
6. No user menu
7. No Quick Actions (`Ctrl+N`)
8. No sidebar collapse (`Ctrl+B`)
9. Emoji in `uz_UZ.json` / bot copy
10. Finance folds Invoices+Payments
11. No Customer 360 tabs
12. WO no Kanban / detail tabs
13. Mini App dark-only
14. Mini App strings not in i18n catalog
15. Top bar “Bildirishnomalar” text vs compact bell
16. CX dialogs force white colors
17. Login page custom colors bypass QSS
18. Sidebar logout hard color
19. Dense settings scroll cards — uneven hierarchy
20. Empty/loading/error states inconsistent across pages
21. Tables without sticky headers / virtualization
22. Dialog-heavy CRUD (prefer drawers)
23. No DPI scale controls
24. Focus policy weakens keyboard nav
25. Status bar incomplete vs blueprint
26. Sync in nav but not in blueprint IA table
27. Duplicate visual systems (desktop QSS vs Mini App CSS)
28. No motion/transition system (150–200ms)
29. Information density uneven (reception dense; dashboard sparse)
30. Alignment inconsistencies in forms (mixed FormLayout spacing)

### Ranked UX / journey issues
1. Cashier must dig through Finance — extra clicks
2. Customer history scattered (list + WO search)
3. Mini App session friction (PIN fallback)
4. Tunnel URL changes break Telegram bookmarks
5. Soft-delete confirm OK; success modal slows experts
6. Global search lacks inventory/invoices
7. Branch filter not obvious on all pages
8. Idle lock good; no license expiry UX in status
9. Reception → WO handoff OK; no print ticket first-class
10. Warranty/CX deep in dialogs — discoverability low
11. Role matrix dialog read-only — no edit UX
12. Backup/restore scary without dry-run preview
13. Telegram inbox vs Mini App reply — two mental models
14. Low-stock alerts not pushed to dashboard attention queue
15. No “what needs me today” unified inbox

---

## 3. Database audit

| Topic | Status | Action |
|-------|--------|--------|
| Soft-delete columns | Good | Keep |
| FK + WAL SQLite | Good | Keep |
| Indexes | Partial | Audit hot columns |
| Alembic | Missing | P1 |
| Postgres path | Engine only | Test + migrate |
| Concurrency | SQLite limits | Postgres for multi-cashier |
| Backup | File copy | Verify integrity hash |
| Permission table | No AuditMixin | OK lookup |
| Normalization | Mostly 3NF | Watch denormalized WO fields |
| Duplicate prevention | Unique SKU/phone | Expand |

**Scale forecast:** 100k WO rows without keyset pagination + indexes → UI freezes. 1M+ needs Postgres, partitioning strategy, archive tables.

---

## 4. Security audit (ranked)

| # | Threat | Status | Priority |
|---|--------|--------|----------|
| 1 | Default `SECRET_KEY` | Open | P1 Critical |
| 2 | Admin password `1234` | Open | P1 Critical |
| 3 | Bot token plaintext DB | Open | P1 Critical |
| 4 | Login lockout present | OK | Monitor |
| 5 | Argon2 passwords | OK | Keep |
| 6 | Session token hashed | OK | Keep |
| 7 | API bearer validate | OK | Add rate limit |
| 8 | Mini App initData HMAC | OK when present | Harden |
| 9 | Staff PIN session tokens | OK | Short TTL + rotate |
| 10 | RBAC nav filter | Partial | Enforce on every service write |
| 11 | No API rate limit | Open | P1 |
| 12 | uploads/ traversal | Review | Whitelist MIME/size |
| 13 | XSS Mini App | Mitigated escapeHtml | CSP headers |
| 14 | CSRF | Low (Bearer) | Document |
| 15 | Audit log coverage | Partial | Finance voids must always audit |
| 16 | Secrets in logs | Risk | Redact tokens |
| 17 | Cloudflare tunnel accountless | Ops risk | Named tunnel |
| 18 | Staff PIN in settings UI | Acceptable with RBAC | Restrict role |
| 19 | SQL via ORM | OK | Ban raw f-strings |
| 20 | Directory listing static | Low | Disable in prod |

---

## 5. Performance audit

1. Eager import of all pages at login
2. Fixed `limit=N` lists without keyset
3. No query explain discipline
4. Dashboard may N+1 without careful repos
5. Image/media CX path unbounded
6. Sync pull size unbounded risk
7. Telegram poller sleep loops OK
8. cloudflared + uvicorn extra processes
9. No Redis/cache layer
10. Qt table loads full result sets
11. Reports PDF generation on UI thread risk
12. Startup `create_all` + patches every launch
13. No connection pool tuning for Postgres
14. Mini App static no CDN (OK local)
15. Memory: long desktop session + poller — monitor

---

## 6. Business logic audit

### Present and real
Reception intake · WO statuses · tech assign · parts/stock · suppliers/PO · invoices/payments/cash · reports · calendar · notifications · Telegram notify/inbox · CX timeline/quote/warranty · branches · license seats · automation rules · AI keyword assistant · sync API

### Missing / weak
1. Customer 360
2. Dedicated cashier Payments UX
3. Refund/reconcile workflows
4. Approval (discount/void)
5. Multi-currency
6. Full accounting/GL
7. Serial/IMEI uniqueness enforcement UI depth
8. Appointment SMS automation depth
9. Franchise multi-tenant billing
10. SLA timers / escalation
11. Technician mobile job board
12. Purchase goods-receipt QC
13. Stocktake / inventory count session
14. Price lists / promotions engine
15. Contract/B2B SLA billing

---

## 7. ERP function completeness

| Module | Status |
|--------|--------|
| CRM (light) | Partial — customers, not 360 |
| Warehouse | Yes |
| Accounting/GL | No |
| Finance ops | Yes (invoice/pay/cash) |
| Reports | Basic |
| Notifications | Yes |
| Calendar | Yes |
| Tasks/Approvals | No |
| Assets | Scaffold |
| Branches | Yes |
| Users/Roles | Yes |
| AI | Local stub |
| Analytics | KPI light |
| Automation | Rules yes |
| Purchase | PO basic |
| Sales POS | No (service ERP) |
| Supplier | Yes |
| Customer Portal | Mini App yes |
| Employee Panel | Mini App + desktop |
| Super Admin multi-tenant SaaS | No |

---

## 8. Code quality (samples)

1. Empty controller packages
2. Duplicate finance vs invoices/payments packages
3. Hardcoded colors bypassing QSS
4. Broad `except Exception` in UI paths
5. Settings `reload` commit side-effects
6. Mini App `window.prompt` for stock qty — unprofessional
7. Schema patches growing unbounded
8. Inconsistent docstring coverage
9. Some services import UI concerns indirectly
10. Test fixtures recreate engines repeatedly (slow suite)
11. `placeholder_page.py` dead
12. Permission seeding vs BA mismatch
13. Telegram HTML messages mixed with plain
14. No mypy gate in CI evidence
15. Ruff may not be enforced in all workflows

---

## 9. Testing gaps

**Have:** auth, customers, WO, inventory, finance, suppliers, CX, calendar, notifications, automation/AI, API sync, admin audit, miniapp, staff bot, tunnel helpers

**Missing:**
1. PySide6 UI tests
2. E2E reception→payment journey
3. Load test 100k rows
4. Security fuzz login
5. Postgres integration
6. Migration upgrade tests
7. Mini App Playwright
8. Concurrent cash session tests
9. Backup/restore integrity
10. RBAC negative tests per route

---

## 10. Scores (detail)

Already in §0. **Overall 58/100.**

Breakdown rationale: architecture and domain logic lift the score; security defaults, testing, and scalability pull it down below “premium ERP” threshold (~75+).

---

## 11. Improvement roadmap

### Priority 1 — Critical (2–4 weeks)
| Task | Time | Diff | Impact | Risk if skipped |
|------|------|------|--------|-----------------|
| Force secrets + admin password wizard | 2–3d | M | Critical | Breach |
| Encrypt bot token | 2d | M | Critical | Bot hijack |
| Alembic migrations | 1–2w | H | High | Upgrade failure |
| Stable Mini App HTTPS | 3–5d | M | High | Field ops broken |
| Toast-first UX | 3–4d | M | High | Perceived amateur |
| Customer 360 | 1–2w | H | High | CRM incomplete |
| Payments cashier page | 1w | M | High | Cashier friction |
| Pagination + indexes | 1w | M | High | Freezes at scale |

### Priority 2 — Professional shell (2–3 weeks)
Design tokens, user menu, lang switch, toast stack, a11y shortcuts, remove hardcoded colors, sync docs.

### Priority 3 — Ops depth (3–5 weeks)
WO Kanban/detail, approvals, PO receiving, stocktake, report packs.

### Priority 4 — Platform (3–4 weeks)
Postgres production, job runner, caching, API rate limits.

### Priority 5 — Expansion (2–4 months)
Web/mobile, GL, multi-currency, true plugins, multi-tenant SaaS.

---

## 12. Professional redesign brief

### Design system
- **8px grid:** 4/8/12/16/24/32/48
- **Type:** Display 20/700 · Title 16/650 · Body 13/400 · Caption 11/500
- **Color:** Primary `#1F4E79`, Accent amber, Success/Danger semantic, 8-step slate
- **Radius:** 8px controls, 10px cards
- **Elevation:** border + surface tone only (no decorative shadows)
- **Motion:** 150ms ease opacity/transform

### Shell
Top: Brand · Search · Branch · Theme · Bell · **User menu**
Left: Collapsible groups Ops / Stock / Money / System
Status: Sync · Bot · Branch · User · **License** · Clock

### Must-have screens
1. Customer 360 (tabs)
2. Payments cashier
3. WO detail + timeline rail
4. Inventory dense table + drawer adjust
5. Settings subnav (Company / Telegram / Users / License / Backup)

### States every list needs
Empty · Loading skeleton · Error retry · Forbidden

---

## 13. Final lists (condensed Top findings)

### Top defects / risks (architecture + runtime)
Default secrets · Admin 1234 · Plaintext bot token · No Alembic · Empty invoice/payment modules · Views bypass controllers · MainWindow import fan-out · Schema patch sprawl · BA≠RBAC keys · Mini App tunnel fragility · No API rate limit · uploads unchecked · No keyset pagination · UI thread report risk · Doc drift CX · Dead placeholder page · Dual company naming · Plugin fake completeness · Postgres untested · Concurrent SQLite cashiers · Missing service-level permission checks · Sync payload size · Eager model imports · Hardcoded QSS bypass · Modal success spam · …

### Top UI problems
Hardcoded brand color · Toast position · No lang switch · No user menu · No quick actions · No collapse sidebar · Finance IA · No 360 · No Kanban · Mini App dark-only · Emoji chrome · Inconsistent empty states · Non-sticky tables · Dialog over drawers · Status bar gaps · Bell as text · CX white dialogs · Login custom styles · Uneven spacing · No skeleton loaders · …

### Top UX problems
Cashier click path · Customer history split · Mini App login friction · Tunnel URL churn · Modal fatigue · Search coverage · Branch discoverability · License visibility · Dual Telegram UIs · Dashboard not an attention queue · Role matrix RO · Backup fear · Warranty buried · Low-stock not surfaced · Print ticket secondary · …

### Top performance risks
Full table loads · No virtualization · Startup create_all · N+1 dashboards · Unbounded sync · Media size · Poller+tunnel processes · No cache · Report on UI thread · Import-all pages · …

### Top security issues
See §4 ranked table (defaults, token, rate limit, uploads, CSP, audit gaps, PIN exposure, log redaction).

### Top code-quality issues
Empty scaffolds · Dead code · Broad excepts · Prompt UI · Docstring gaps · Naming collisions · Test speed · No enforced typing CI · …

### Top professional recommendations
1. Ship P1 security before sales demos on customer PCs
2. Alembic immediately
3. Customer 360 + Payments page for blueprint parity
4. Toast-first redesign week
5. Named HTTPS for Mini App
6. Pagination standard library helper
7. Service-layer `require_permission` decorator
8. Delete or implement empty modules
9. UI E2E smoke (login→intake→pay)
10. Postgres staging environment

### Top premium ERP features to add next
Customer 360 · Cashier Payments · Approvals · Stocktake · WO Kanban · SLA escalations · Named tunnel SSO Mini App · GL lite · Multi-branch consolidated reports · Technician mobile · Contract billing · Refunds · Serial registry · Price lists · E2E automation suite · …

---

## Closing

SMOXI Service is a **real service-management ERP core**, not a toy demo. Architecture and domain depth are above typical freelancers’ apps. To reach **Microsoft / Linear / Odoo-class** commercial quality, prioritize **security defaults, migrations, cashier/360 UX, and scale hygiene** before adding more modules.

**Next recommended sprint:** P1 security + Alembic + Payments page + toast UX (≈ 3–4 weeks with one senior full-stack).
