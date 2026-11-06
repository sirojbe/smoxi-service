# SMOXI Service — Engineering Standards

**Document status:** Official
**Version:** 1.0.0
**Effective date:** 2026-07-23
**Applies to:** All modules, developers, reviewers, and AI assistants
**Scope:** Phase 2 and all subsequent development

This document is the **mandatory** software engineering guideline for SMOXI Service.
Every future file, feature, and change **must** comply without exception.

> **Phase 2 note:** This phase defines standards only. No business modules, UI screens, or database tables are introduced here. Code snippets below are **illustrative examples**, not production features.

---

## Table of Contents

1. [Folder Naming Rules](#1-folder-naming-rules)
2. [Python File Naming Rules](#2-python-file-naming-rules)
3. [Class Naming Rules](#3-class-naming-rules)
4. [Function Naming Rules](#4-function-naming-rules)
5. [Variable Naming Rules](#5-variable-naming-rules)
6. [Constant Naming Rules](#6-constant-naming-rules)
7. [Enum Naming Rules](#7-enum-naming-rules)
8. [Database Model Naming Rules](#8-database-model-naming-rules)
9. [Repository Naming Rules](#9-repository-naming-rules)
10. [Service Naming Rules](#10-service-naming-rules)
11. [UI Page Naming Rules](#11-ui-page-naming-rules)
12. [Widget Naming Rules](#12-widget-naming-rules)
13. [Dialog Naming Rules](#13-dialog-naming-rules)
14. [Configuration Naming Rules](#14-configuration-naming-rules)
15. [Logging Standards](#15-logging-standards)
16. [Exception Handling Standards](#16-exception-handling-standards)
17. [Validation Standards](#17-validation-standards)
18. [Database Access Rules](#18-database-access-rules)
19. [Dependency Injection Rules](#19-dependency-injection-rules)
20. [Repository Pattern Rules](#20-repository-pattern-rules)
21. [Service Layer Rules](#21-service-layer-rules)
22. [UI Layer Rules](#22-ui-layer-rules)
23. [Business Logic Rules](#23-business-logic-rules)
24. [Configuration Rules](#24-configuration-rules)
25. [Localization Rules](#25-localization-rules)
26. [Translation Rules](#26-translation-rules)
27. [API Rules](#27-api-rules)
28. [Security Rules](#28-security-rules)
29. [Performance Rules](#29-performance-rules)
30. [Testing Rules](#30-testing-rules)
31. [Git Commit Rules](#31-git-commit-rules)
32. [Branch Naming Rules](#32-branch-naming-rules)
33. [Pull Request Rules](#33-pull-request-rules)
34. [Release Rules](#34-release-rules)
35. [Documentation Rules](#35-documentation-rules)
36. [Comment Rules](#36-comment-rules)
37. [Code Formatting Rules](#37-code-formatting-rules)
38. [Import Order Rules](#38-import-order-rules)
39. [Error Message Standards](#39-error-message-standards)
40. [Notification Standards](#40-notification-standards)

---

## Guiding Principles

| Principle | Requirement |
|-----------|-------------|
| **Consistency** | Same patterns, names, and structure everywhere |
| **Maintainability** | Clear layers; easy to change one concern without breaking others |
| **Scalability** | Modules grow independently; no god classes |
| **Security** | Secure by default; validate everything |
| **Performance** | Never block the UI; use efficient queries |
| **Readability** | Names explain intent; comments explain *why* |
| **Expandability** | New markets, locales, and modules without rewrites |

**Architecture style:** Clean Architecture + Modular Monolith
**Patterns:** Repository, Service Layer, Dependency Injection
**Language style:** PEP 8, type hints everywhere on public APIs

---

## 1. Folder Naming Rules

| Rule | Standard |
|------|----------|
| Style | `snake_case` only |
| Characters | Lowercase letters, digits, underscores |
| Forbidden | Spaces, hyphens, PascalCase, camelCase |
| Feature modules | Live under `app/modules/<feature_name>/` |
| Required subfolders per module | `views/`, `controllers/`, `services/`, `repositories/`, `models/`, `schemas/`, `resources/` |

**Examples**

| Correct | Incorrect |
|---------|-----------|
| `work_orders` | `WorkOrders`, `work-orders` |
| `app/modules/inventory/` | `app/Modules/Inventory/` |
| `assets/styles/` | `assets/Styles/` |

**Empty / runtime folders** keep a `.gitkeep` so Git tracks the directory.

---

## 2. Python File Naming Rules

| Rule | Standard |
|------|----------|
| Style | `snake_case.py` |
| One primary concept per file | Prefer cohesion over “utils dumping grounds” |
| Tests | `test_<module>_<subject>.py` under `tests/` |
| Private helpers | Leading underscore file only if package-private and documented |

**Layer suffixes (required when role is not obvious from folder):**

| Layer | Filename pattern | Example |
|-------|------------------|---------|
| Model | `<entity>_model.py` or `<entity>.py` in `models/` | `customer.py` |
| Schema | `<entity>_schema.py` or `<entity>.py` in `schemas/` | `customer.py` |
| Repository | `<entity>_repository.py` | `customer_repository.py` |
| Service | `<entity>_service.py` | `customer_service.py` |
| Controller | `<entity>_controller.py` | `customer_controller.py` |
| View / Page | `<entity>_page.py` | `customer_list_page.py` |
| Widget | `<name>_widget.py` | `status_badge_widget.py` |
| Dialog | `<name>_dialog.py` | `confirm_delete_dialog.py` |

---

## 3. Class Naming Rules

| Kind | Convention | Example |
|------|------------|---------|
| General class | `PascalCase` | `WorkOrderAllocator` |
| Abstract base | `PascalCase` + optional `Base` / `ABC` | `BaseRepository` |
| Exception | `PascalCase` + `Error` / `Exception` | `ValidationError` |
| Mixin | `PascalCase` + `Mixin` | `SoftDeleteMixin` |
| Protocol / interface | `PascalCase` + optional `Protocol` | `UnitOfWork` |
| Qt widget subclass | Descriptive `PascalCase` | `PrimaryButton` |

**Forbidden:** Hungarian notation (`CCustomer`), abbreviations without glossary entry (`WOMgr`).

```python
class CustomerService:
    """Application service for customer use cases."""
```

---

## 4. Function Naming Rules

| Kind | Convention | Example |
|------|------------|---------|
| Public function / method | `snake_case`, verb-first | `create_customer` |
| Boolean query | `is_`, `has_`, `can_`, `should_` | `is_active` |
| Private | Leading `_` | `_normalize_phone` |
| Async | Same names; use `async def` | `async def sync_orders` |
| Factory | `create_`, `build_`, `from_` | `create_application_context` |

**Rules**

- One responsibility per function.
- Prefer return values over mutating many out-parameters.
- Max complexity: keep functions short; extract helpers when nested logic grows.

```python
def calculate_tax(amount: Decimal, rate: Decimal) -> Decimal:
    """Return tax for *amount* at *rate* (0–1)."""
```

---

## 5. Variable Naming Rules

| Kind | Convention | Example |
|------|------------|---------|
| Local / instance | `snake_case` | `order_total` |
| Boolean | Affirmative `is_` / `has_` | `is_synced` |
| Collection | Plural noun | `customers` |
| Map | `*_by_*` or `*_map` | `customer_by_id` |
| Unused | `_` | `for _ in range(3)` |

**Forbidden:** single-letter names except loop indices (`i`, `j`) in tiny scopes; `data`, `temp`, `obj` without context.

**No module-level mutable globals.** Use settings, DI, or explicit context objects.

---

## 6. Constant Naming Rules

| Kind | Convention | Location |
|------|------------|----------|
| Module / package constants | `UPPER_SNAKE_CASE` | `app/config/constants.py` or module top |
| Enum members | `UPPER_SNAKE_CASE` | Enum class |
| Magic numbers | Never inline | Named constant |

```python
MAX_LOGIN_ATTEMPTS: Final[int] = 5
DEFAULT_PAGE_SIZE: Final[int] = 50
```

UI-visible strings are **not** constants in Python source — they belong in translation catalogs (see §25–§26).

---

## 7. Enum Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Enum class | `PascalCase` | `WorkOrderStatus` |
| Members | `UPPER_SNAKE_CASE` | `IN_PROGRESS` |
| Values | Stable strings/ints for DB/API | `"in_progress"` |

Prefer `enum.StrEnum` for API/DB-facing values.

```python
from enum import StrEnum

class SyncStatus(StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"
```

---

## 8. Database Model Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| SQLAlchemy model class | Singular `PascalCase` | `Customer` |
| Table name | Plural `snake_case` | `customers` |
| Column name | `snake_case` | `display_name` |
| FK column | `<singular>_id` | `company_id` |
| Association table | `snake_case` plural pair | `work_order_parts` |

### Mandatory columns (every business table)

| Column | Type (logical) | Notes |
|--------|----------------|-------|
| `id` | Integer PK (or BigInteger) | Surrogate key |
| `uuid` | UUID / string(36) | Stable cross-system identity |
| `created_at` | DateTime (UTC) | Set on insert |
| `updated_at` | DateTime (UTC) | Set on update |
| `created_by` | FK / user id nullable | Actor who created |
| `updated_by` | FK / user id nullable | Actor who last updated |
| `deleted_at` | DateTime nullable | Soft delete marker |
| `version` | Integer | Optimistic concurrency |
| `sync_status` | Enum / string | Cloud sync state |

**Hard deletes are forbidden** for business data. Use soft delete (`deleted_at`).

---

## 9. Repository Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Interface / ABC | `PascalCase` + `Repository` | `CustomerRepository` |
| Implementation | Optional backend suffix | `SqlAlchemyCustomerRepository` |
| File | `<entity>_repository.py` | `customer_repository.py` |
| Methods | Persistence verbs | `get_by_id`, `add`, `save`, `list`, `soft_delete` |

Repositories **must not** contain business rules (pricing, permissions, workflows).

---

## 10. Service Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Class | `PascalCase` + `Service` | `InvoiceService` |
| File | `<domain>_service.py` | `invoice_service.py` |
| Methods | Use-case oriented | `issue_invoice`, `void_invoice` |

One primary aggregate / bounded context per service class. Orchestrate repositories; do not talk to Qt widgets.

---

## 11. UI Page Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Class | `PascalCase` + `Page` | `CustomerListPage` |
| File | `<name>_page.py` | `customer_list_page.py` |
| Module path | `app/modules/<feature>/views/` | |

Pages compose widgets and call controllers/services. Pages **do not** run SQL.

---

## 12. Widget Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Class | `PascalCase` + `Widget` (or descriptive Qt name) | `MoneyAmountWidget` |
| File | `<name>_widget.py` | `money_amount_widget.py` |
| Location | `app/widgets/` (shared) or module `resources/` / local views | |

Prefer reusable widgets over copy-pasted layouts.

---

## 13. Dialog Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Class | `PascalCase` + `Dialog` | `ConfirmDeleteDialog` |
| File | `<name>_dialog.py` | `confirm_delete_dialog.py` |
| Result | Explicit accepted/rejected + typed payload | |

Dialogs must be localizable and theme-aware (dark/light).

---

## 14. Configuration Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| Settings class | `PascalCase` + `Settings` | `DatabaseSettings` |
| Factory | `get_<name>_settings` | `get_settings()` |
| Env vars | `SMOXI_`, `SMOXI_DB_`, `SMOXI_SECURITY_` | `SMOXI_DEBUG` |
| Config files | `snake_case` under `config/` or `app/config/` | `settings.py` |

Never commit real secrets. Use `.env` (gitignored) and `.env.example` templates.

---

## 15. Logging Standards

**Library:** Loguru (configured in `app/config/logging.py`).

### Must log

| Event category | Examples |
|----------------|----------|
| Auth | Login, logout, failed login, lockout |
| Data lifecycle | Create, update, soft delete |
| Sync | Start, success, conflict, failure |
| Ops | Backup, restore |
| Security | Permission denied, token invalid, suspicious activity |
| Failures | Application, database, API errors |

### Rules

1. Log **structured context** (ids, actor, module) — never passwords, tokens, or full card numbers.
2. Levels: `DEBUG` (dev detail), `INFO` (business events), `WARNING` (recoverable), `ERROR` (failed operation), `CRITICAL` (system unusable).
3. UI must never depend on log text for control flow.
4. Correlate multi-step flows with a request/correlation id when available.

```python
logger.info(
    "customer_created",
    customer_uuid=str(customer.uuid),
    actor_id=actor_id,
)
```

---

## 16. Exception Handling Standards

| Rule | Detail |
|------|--------|
| Domain errors | Custom exceptions under module or `app/core` |
| Catch specificity | Catch the narrowest exception type |
| Never bare `except:` | Forbidden |
| User visibility | Friendly localized message only |
| Tracebacks | Logs only — **never** show Python tracebacks in UI |
| Recovery | Retry/backoff for transient I/O when safe; otherwise fail gracefully |

```python
# Illustrative pattern
try:
    service.create_customer(payload)
except ValidationError as exc:
    logger.warning("validation_failed", reason=str(exc))
    ui.show_error(tr("errors.validation_failed"))
except AppError as exc:
    logger.exception("customer_create_failed")
    ui.show_error(tr("errors.unexpected"))
```

---

## 17. Validation Standards

1. Validate **at system boundaries** (UI input, API request, import files).
2. Use **Pydantic models** for structured payloads (`app/.../schemas/`).
3. Re-validate in the **service layer** for critical business invariants.
4. Never trust client-side checks alone.
5. Normalize before validate (trim, case, phone formats) in one place.

```python
from pydantic import BaseModel, Field, EmailStr

class CustomerCreateSchema(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
```

---

## 18. Database Access Rules

| Rule | Requirement |
|------|-------------|
| Access path | UI → Controller → Service → Repository → ORM/DB |
| Direct SQL in UI | Forbidden |
| Soft delete | Filter `deleted_at IS NULL` by default |
| Transactions | Required for multi-step writes |
| Concurrency | Honor `version` (optimistic locking) |
| Duplication | Normalize; no redundant copies of master data |
| Migrations | Alembic only — no manual prod schema edits |
| UTC | Store timestamps in UTC |

```python
# Illustrative: transactional unit of work (concept)
with unit_of_work:
    repo.add(entity)
    unit_of_work.commit()
```

---

## 19. Dependency Injection Rules

1. Prefer **constructor injection** of repositories and collaborators.
2. Composition root: application bootstrap (`ApplicationContext` / future container).
3. No service locator anti-pattern in business code.
4. UI obtains services via controller/factory — not global singletons (except settings/logger factories).
5. Depend on **abstractions** (protocols/ABCs) where multiple backends exist (SQLite vs PostgreSQL).

```python
class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository
```

---

## 20. Repository Pattern Rules

| Allowed | Forbidden |
|---------|-----------|
| CRUD / query methods | Business workflows |
| Mapping ORM ↔ domain | Showing dialogs |
| Soft delete helpers | Calling external HTTP for business decisions |
| Spec/filter objects | Hard-coded UI strings |

Default query methods exclude soft-deleted rows unless `include_deleted=True`.

---

## 21. Service Layer Rules

1. Services own **use cases** and **transactions** boundaries.
2. Services call one or more repositories.
3. Services emit domain events / logs for important actions.
4. Services return DTOs/schemas or domain objects — not Qt widgets.
5. Authorization checks belong in service (or dedicated policy) — not only in UI.

---

## 22. UI Layer Rules

Every page **must**:

| Requirement | Detail |
|-------------|--------|
| Spacing | Use shared layout tokens / style constants |
| Themes | Support **Dark Mode** and **Light Mode** |
| Localization | All user-visible strings via translation API |
| Scaling | Layouts work on common Windows resolutions and DPI |
| Reuse | Prefer shared widgets over one-off copies |
| Responsiveness | **Never freeze the UI** |
| Async | Long I/O / sync / reports run off the UI thread (`QThread`, workers, or async bridges) |

**Forbidden in views**

- Business rules (pricing, stock allocation)
- Direct database/session usage
- Hardcoded colors that break themes (use palette/tokens)

---

## 23. Business Logic Rules

1. Business logic lives in **services** (and pure domain helpers), not in views or repositories.
2. Keep domain rules **testable without Qt**.
3. No duplicated rules across modules — extract shared domain packages when needed.
4. Side effects (email, Telegram, sync) go through explicit ports/adapters.

---

## 24. Configuration Rules

1. Environment-specific values via **Pydantic Settings**.
2. Feature flags (when introduced) are named `SMOXI_FEATURE_*` and documented.
3. Defaults must be safe for development; production requires explicit secrets.
4. Changing config must not require code edits for ops parameters (URLs, pool sizes, locales).

---

## 25. Localization Rules

| Rule | Detail |
|------|--------|
| Default locale | `uz_UZ` (asosiy UI tili — oʻzbekcha; qarang: BusinessAnalysis.md) |
| Supported locales | Declared centrally; UI language switchable |
| Source of truth | Translation catalogs under `assets/translations/` |
| Runtime | Qt translation (`.ts` / `.qm`) and/or project i18n helpers |
| Formatting | Locale-aware dates, numbers, currency |

Never concatenate translated fragments in ways that break grammar — use named placeholders.

---

## 26. Translation Rules

1. Keys use **dot namespaces**: `customers.list.title`, `errors.network_unavailable`.
2. English source strings or keys must be reviewed for translators.
3. No raw English in production UI code paths once i18n is enabled for a module.
4. Plurals and gender-sensitive languages must use proper plural forms where supported.
5. Screenshots / context notes for translators live in module docs when UI is complex.

```text
# Illustrative key style
customers.actions.create
errors.validation_failed
security.session_expired
```

---

## 27. API Rules

| Topic | Standard |
|-------|----------|
| Framework | FastAPI |
| Versioning | Prefix `/api/v1` |
| Schemas | Pydantic request/response models |
| Errors | Consistent error envelope (code, message, details) |
| Auth | Token/session scheme defined by security module |
| Docs | OpenAPI generated; keep descriptions accurate |
| Idempotency | Required for critical POST retries where applicable |

Desktop and API **share** schemas/services where practical — do not fork business rules.

---

## 28. Security Rules

| Rule | Requirement |
|------|-------------|
| Passwords | Never store plaintext; hash with strong KDF (e.g. Argon2/bcrypt) |
| Input | Validate and sanitize all external input |
| SQL | ORM/parameterized queries only — no string-built SQL |
| XSS | Escape/encode where web surfaces exist; treat rich text carefully |
| Brute force | Lockout / rate limit on authentication |
| Authorization | Check permissions server-side / service-side every time |
| Sessions | Protect against hijacking (secure tokens, expiry, rotation) |
| Secrets | Env/secret store only; rotate on leak |
| Logging | Redact PII/secrets |

---

## 29. Performance Rules

1. No blocking network/DB work on the Qt main thread.
2. Paginate large lists; avoid loading entire tables into memory.
3. Use eager/joined loading deliberately — prevent N+1 queries.
4. Index columns used in filters/joins (documented in Database docs).
5. Profile before micro-optimizing; measure sync and report jobs.
6. Cache only with explicit invalidation strategy.

---

## 30. Testing Rules

| Layer | Expectation |
|-------|-------------|
| Unit | Domain/services with fakes/mocks — no real UI |
| Integration | Repositories against SQLite test DB |
| API | `httpx` + FastAPI test client |
| UI | Selective; prefer testing controllers/view-models first |
| Naming | `test_<behavior>` |
| Location | `tests/` mirroring `app/` |

Every bugfix should include a regression test when feasible.

CI (when enabled) must run lint + unit tests before merge.

---

## 31. Git Commit Rules

### Format

```text
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

### Types

| Type | Use |
|------|-----|
| `feat` | New user-facing capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting; no behavior change |
| `refactor` | Restructure without feature/fix |
| `perf` | Performance improvement |
| `test` | Tests only |
| `build` | Packaging / pyproject / Nuitka |
| `ci` | CI pipelines |
| `chore` | Maintenance |
| `security` | Security fix |

### Rules

- Summary ≤ 72 characters; imperative mood (“add”, not “added”).
- One logical change per commit when practical.
- Never commit secrets, `logs/`, local DB files, or build artifacts.
- Reference issue IDs in footer when applicable: `Refs: #123`.

**Examples**

```text
docs(standards): add official engineering standards

feat(customers): add customer list page

fix(auth): prevent session reuse after logout
```

---

## 32. Branch Naming Rules

| Pattern | Purpose | Example |
|---------|---------|---------|
| `main` | Production-ready line | `main` |
| `develop` | Integration line (if used) | `develop` |
| `feature/<scope>-<short>` | Features | `feature/customers-list` |
| `fix/<scope>-<short>` | Bugfixes | `fix/invoice-tax-rounding` |
| `hotfix/<scope>-<short>` | Urgent prod fix | `hotfix/login-lockout` |
| `release/vX.Y.Z` | Release prep | `release/v1.2.0` |
| `docs/<short>` | Documentation | `docs/engineering-standards` |
| `chore/<short>` | Tooling | `chore/ruff-config` |

Use lowercase `kebab-case` segments. No personal names as the only branch label.

---

## 33. Pull Request Rules

Every PR **must** include:

1. Clear title following commit type style.
2. Summary of *why* and *what*.
3. Test plan (checklist).
4. Screenshots for UI changes.
5. Risk / rollback notes for data or security changes.
6. Confirmation of Engineering Standards compliance.

**Merge requirements**

- Lint clean (`ruff`)
- Tests passing
- At least one review (human) for `main`
- No unresolved critical comments

Keep PRs focused; prefer small, reviewable diffs.

---

## 34. Release Rules

### Version numbering (SemVer)

```text
vMAJOR.MINOR.PATCH
```

| Bump | When |
|------|------|
| **MAJOR** | Breaking changes (API, data, UX contracts) |
| **MINOR** | Backward-compatible features |
| **PATCH** | Backward-compatible fixes |

**Examples:** `v1.0.0`, `v1.1.0`, `v2.0.0`

### Release checklist

1. Update `docs/ChangeLog.md`
2. Bump version in `pyproject.toml` / settings default
3. Tag Git: `vX.Y.Z`
4. Build with Nuitka
5. Produce Inno Setup installer
6. Smoke-test install on clean Windows VM
7. Publish artifacts to the approved release channel

Pre-releases: `v1.2.0-rc.1` when needed.

---

## 35. Documentation Rules

### Project-level (`docs/`)

| Document | Purpose |
|----------|---------|
| `EngineeringStandards.md` | This file — mandatory rules |
| `Architecture.md` | System architecture |
| `Database.md` | Schema & migration policy |
| `API.md` | HTTP API conventions |
| `Roadmap.md` | Planned phases |
| `ChangeLog.md` | Released changes |

### Every feature module **must** contain

| Artifact | Purpose |
|----------|---------|
| `README.md` | Module purpose and boundaries |
| Architecture description | How the module fits layers |
| Dependencies | Other modules/services required |
| Public API description | Services/schemas other modules may use |
| Change History | Module-level notable changes |
| Developer Notes | Pitfalls, invariants, TODOs |

Update docs in the **same PR** as behavior changes.

---

## 36. Comment Rules

| Do | Don't |
|----|-------|
| Explain **why** and non-obvious constraints | Narrate what the next line does |
| Document public module/class/function intent | Leave dead commented-out code |
| Mark deliberate exceptions with justification | Use comments instead of better names |
| Keep TODOs actionable: `TODO(owner): …` | Vague `TODO: fix later` |

Use docstrings (PEP 257) on public APIs. Prefer type hints over prose for parameter types.

---

## 37. Code Formatting Rules

| Tool / rule | Standard |
|-------------|----------|
| Style | PEP 8 |
| Line length | 100 (see `pyproject.toml` / Ruff) |
| Formatter / linter | Ruff |
| Type checker | mypy (strict for `app/`) |
| Quotes | Prefer double quotes for consistency with Ruff defaults unless file history differs |
| Trailing commas | Encouraged in multi-line literals |

Do not disable lint rules without a documented reason on that line/file.

---

## 38. Import Order Rules

Order (separated by blank lines):

1. Future imports (`from __future__ import annotations`)
2. Standard library
3. Third-party (`PySide6`, `fastapi`, `sqlalchemy`, …)
4. First-party (`app...`)

Within each group: alphabetical. Prefer absolute imports (`from app.config.settings import get_settings`).

```python
from __future__ import annotations

from decimal import Decimal

from loguru import logger
from pydantic import BaseModel

from app.config.settings import get_settings
```

No wildcard imports (`from module import *`).

---

## 39. Error Message Standards

| Audience | Content |
|----------|---------|
| End user | Short, localized, actionable — no stack traces, no SQL |
| Log / support | Detailed, technical, with codes and context ids |
| API | Stable `code` + localized/human `message` + optional `details` |

**Pattern**

- User: “Unable to save the customer. Check required fields and try again.”
- Log: `customer_create_failed` + validation fields + actor + correlation id

Error codes (when introduced): `SMOXI-<DOMAIN>-<NUMBER>` e.g. `SMOXI-AUTH-001`.

---

## 40. Notification Standards

| Channel | Use |
|---------|-----|
| In-app toast / banner | Non-blocking success/info/warning |
| Modal dialog | Decisions that require acknowledgement |
| System tray (optional) | Background sync / long jobs |
| Telegram / email (future) | External alerts per user preferences |

**Rules**

1. Notifications are localized.
2. Do not spam — coalesce repeated events.
3. Success messages for critical writes; avoid noise for trivial navigation.
4. Security events may notify admins without revealing sensitive detail to unauthorized users.
5. Persist important alerts in the notifications module when implemented.

Severity levels: `info`, `success`, `warning`, `error`.

---

## Layer Dependency Rule (Summary)

```text
UI (views/widgets/dialogs)
    ↓
Controllers
    ↓
Services  ←—— authorization, transactions, use cases
    ↓
Repositories
    ↓
Database / External systems
```

**Dependencies point inward.** Outer layers may depend on inner layers; never the reverse.

---

## Python Style Checklist (Quick Reference)

- [ ] PEP 8 + Ruff clean
- [ ] Type hints on public functions and attributes
- [ ] Dataclasses / Pydantic models for data carriers
- [ ] Enums for closed value sets
- [ ] Properties for derived attributes
- [ ] Context managers for resources and transactions
- [ ] Meaningful names; no duplicated logic
- [ ] No magic numbers; no hardcoded user strings
- [ ] No mutable global state

---

## Compliance

| Role | Duty |
|------|------|
| Developer / AI assistant | Follow this document on every change |
| Reviewer | Reject PRs that violate standards |
| Architect | Update this document via versioned PR only |

**Document changes** require a PR titled `docs(standards): …` and a `ChangeLog` entry under Documentation.

---

## Document History

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-07-23 | Initial official Engineering Standards (Phase 2) |

---

*End of SMOXI Service Engineering Standards*
