# SMOXI Service — Master Development Prompt

**Document status:** Official (binding)
**Version:** 1.0.0
**Effective date:** 2026-07-23
**Codename:** Ultimate Master Development Prompt

This document is the **product charter and global development contract** for SMOXI Service.
It governs every architect, engineer, QA, DevOps, security, and AI assistant working on the product.

**Companion mandatory documents**

| Document | Role |
|----------|------|
| [EngineeringStandards.md](EngineeringStandards.md) | Coding, Git, security, layer rules |
| [UIUXBlueprint.md](UIUXBlueprint.md) | Screens, navigation, design system |
| [Architecture.md](Architecture.md) | System architecture (evolving) |
| [Database.md](Database.md) | Persistence strategy (evolving) |
| [API.md](API.md) | HTTP API conventions (evolving) |
| [Roadmap.md](Roadmap.md) | Phase and module order |

If documents conflict: **Master Development Prompt** sets product intent; **Engineering Standards** win for code mechanics; **UI/UX Blueprint** wins for screen/UX contracts. Resolve conflicts explicitly in a docs PR before coding.

---

## 1. Product Definition

| Item | Value |
|------|--------|
| **Name** | SMOXI Service |
| **Type** | Enterprise Service Management ERP |
| **Primary platform** | Windows Desktop (`.exe`) |
| **Future platforms** | Web, Android, iOS, Telegram Mini App |
| **Language** | Python 3.14+ |
| **GUI** | PySide6 |
| **Backend** | FastAPI |
| **ORM** | SQLAlchemy 2.x |
| **Offline DB** | SQLite |
| **Cloud DB** | PostgreSQL |
| **Migrations** | Alembic |
| **Reports** | ReportLab, OpenPyXL |
| **Notifications** | Telegram (future) |
| **Sync model** | Offline-first |
| **Architecture** | Enterprise Modular + Clean Architecture |

**Commercial bar:** This is not a demo or sample. Every decision must support a product sellable to service centers worldwide — scalable, maintainable, reliable, secure.

---

## 2. Non-Negotiable Engineering Rules

1. Never generate quick hacks, demo code, or throwaway architecture.
2. Never simplify architecture for short-term speed.
3. Never ignore scalability, security, or operability.
4. Every module must be production-ready before the next module starts.
5. Every class has one responsibility (SRP).
6. Every file has a clear purpose; no dumping grounds.
7. No duplicated logic — extract shared domain carefully.
8. PEP 8 + project Ruff/mypy configuration.
9. Type hints on all public APIs.
10. Meaningful names; document every public class and method.
11. Never hardcode secrets, credentials, or environment-specific values.
12. Every error is logged with context; users never see tracebacks.
13. No unfinished code, no `TODO` left in shipped modules, no placeholder/fake methods.
14. Prefer asking over assuming when requirements are missing.

### Global change-control rules

- Never rewrite existing modules unless requested.
- Never remove existing functionality without an approved migration path.
- Always preserve backward compatibility for data and public APIs.
- Before creating a new file, check whether a similar file already exists.
- If an architectural conflict is found, **explain it and get agreement** before changing.
- Finish one module completely before starting another.
- Every generated line must be production-ready for that module’s scope.

---

## 3. Architecture Mandates

| Concern | Mandate |
|---------|---------|
| Patterns | Repository · Service Layer · DI-ready · SOLID · Clean Architecture |
| Layers | UI → Controllers → Services → Repositories → Database/External |
| Offline | SQLite local; sync-ready fields (`uuid`, `sync_status`, `version`) |
| Cloud | PostgreSQL for multi-user / multi-branch |
| Soft delete | No hard deletes for business data |
| Audit | `created_at/by`, `updated_at/by`, `deleted_at`, history where required |
| Identity | UUID for cross-system identity; surrogate `id` for local PK |
| Security | Hashed passwords, RBAC, sessions, validation, audit trail |
| Logging | Auth, CRUD, restore, sync, errors, warnings, perf, security, DB, API |
| Extensibility | Plugin-ready, AI-ready, API-ready, cloud-sync-ready |

---

## 4. Core Feature Map

Authentication · Users · Roles · Permissions · Companies · Branches · Customers · Reception · Devices · Work Orders · Diagnostics · Repair Process · Technicians · Inventory · Warehouse · Suppliers · Purchasing · Invoices · Payments · Expenses · Finance · Reports · Calendar · Notifications · Settings · License Management · Audit Logs · Backup · Restore · Localization · Themes · Plugin System · AI Ready · API Ready · Cloud Sync Ready

Feature UX and screens: see **UI/UX Blueprint**.
Feature code rules: see **Engineering Standards**.

---

## 5. Work Order Lifecycle (Canonical)

```text
Customer arrives
  → Reception creates Work Order
  → Customer saved
  → Device saved
  → Issue description recorded
  → Photos attached
  → Accessories recorded
  → Work Order created (Status: Received)
  → Technician assigned
  → Diagnosis started → Diagnosis completed
  → Repair quotation prepared
  → Customer approval required
  → If approved → Repair started
  → Testing → Quality Control
  → Ready for Pickup → Delivered
  → Warranty activated → Closed
```

**Status history rule:** Every status change stores **user**, **timestamp**, and **notes**. Illegal transitions are rejected by the service layer.

---

## 6. Domain Quality Bars

### Inventory

Track parts, movements, stock history, warehouse transfers, minimum stock, suppliers, purchase/selling prices, serials; barcode and QR support.

### Finance

Invoices, payments, cash register, expenses, income, profit, refunds, taxes, daily closing, monthly/annual reports; Excel/PDF export.

### Customer experience

Complete customer history; per-device history; every work order stores timeline, notes, photos, files, technician, status changes, cost breakdown, warranty, invoices, payments, and links to future repairs.

### Reports

A4, A5, thermal receipt, barcode, QR, PDF, Excel, CSV, charts, statistics — professional print layouts.

### Backup

Automatic + manual backup, restore, cloud-ready, version history.

---

## 7. Module Delivery Process (Mandatory)

For **each** module, execute in order. Do not skip. Do not code before steps 1–10 are written and accepted for that module.

| Step | Name | Output |
|------|------|--------|
| 1 | Business Analysis | Goals, actors, scope, out-of-scope |
| 2 | Functional Specification | Behaviors, permissions, edge cases |
| 3 | Technical Design | Layers, classes, DI, packages |
| 4 | Database Design | Tables, indexes, migrations plan |
| 5 | UI Design | Pages/dialogs mapped to Blueprint |
| 6 | Repository Layer | Interfaces + implementations |
| 7 | Service Layer | Use cases + transactions |
| 8 | Validation | Schemas + invariants |
| 9 | Error Handling | Domain errors + user messages |
| 10 | Logging | Event catalog for the module |
| 11 | Testing | Unit/integration plan + tests |
| 12 | Documentation | Module README + public API |
| 13 | Implementation | Production code only |
| 14 | Code Review | Standards + Blueprint compliance |
| 15 | Integration | Wire into shell, permissions, nav |

### Pre-implementation checklist (must answer before coding)

1. Purpose of the module
2. Architecture
3. Classes
4. Services
5. Repositories
6. UI pages
7. Dialogs
8. Workflows
9. Validations
10. Future extensibility

---

## 8. Recommended Module Order

Foundation already delivered: project structure, engineering standards, UI/UX blueprint.

| Order | Module | Why this order |
|-------|--------|----------------|
| A | **Platform Core** | DB engine/session, base model mixins, DI composition root, logging/audit hooks |
| B | **Desktop Shell** | Main window, top bar, sidebar, status bar, theme/locale plumbing (no domain) |
| C | **Security Foundation** | Auth, users, roles, permissions, sessions |
| D | **Organization** | Companies, branches |
| E | **Customers & Devices** | Customer 360, device registry |
| F | **Reception & Work Orders** | Intake + full WO lifecycle |
| G | **Technicians** | Assignment, workload |
| H | **Inventory & Warehouse** | Stock, movements, transfers |
| I | **Suppliers & Purchasing** | PO, receiving |
| J | **Finance** | Invoices, payments, cash, expenses |
| K | **Reports** | PDF/Excel/thermal |
| L | **Calendar & Notifications** | Scheduling, alerts |
| M | **Settings, License, Backup** | Ops & commercial controls |
| N | **API / Sync / Plugins / AI** | Expansion surfaces |

Exact Phase numbering is maintained in [Roadmap.md](Roadmap.md). Deviations require explicit approval.

---

## 9. Quality Gate (Definition of Done)

A module is **done** only when:

- [ ] Steps 1–15 completed and documented
- [ ] Engineering Standards satisfied
- [ ] UI/UX Blueprint screens implemented or explicitly deferred with Blueprint update
- [ ] Migrations apply cleanly on SQLite (and PostgreSQL when in scope)
- [ ] Soft delete + audit + UUID rules applied
- [ ] RBAC enforced in service layer
- [ ] Logging for create/update/delete/security events
- [ ] Tests cover critical paths
- [ ] Module `README.md` + public API notes exist
- [ ] No TODOs, stubs, or fake returns in shipped paths
- [ ] Integrated into navigation/permissions without breaking prior modules

---

## 10. Priority Statement

> Always prioritize **architecture quality** over development speed.
> Build SMOXI Service as premium enterprise software that can compete with international repair management systems — reliable, scalable, secure, maintainable, and ready for Web, Android, iOS, and Telegram Mini App.

---

## Document History

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-07-23 | Initial Master Development Prompt ratified |

---

*End of Master Development Prompt*
