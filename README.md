# SMOXI Service

International Service Management ERP Platform — Windows desktop application with FastAPI backend capabilities.

This repository contains the commercial product foundation for **SMOXI Service**:

| Phase | Deliverable |
|-------|-------------|
| 1 | Project structure & config starters |
| 2 | [Engineering Standards](docs/EngineeringStandards.md) |
| 3 | [UI/UX Blueprint](docs/UIUXBlueprint.md) |
| 4 | [Master Development Prompt](docs/MasterDevelopmentPrompt.md) |
| 5 | [Biznes Tahlili & FS](docs/BusinessAnalysis.md) (oʻzbekcha) |

**Interfeys tili:** oʻzbekcha (asosiy). Domain modullar Master Prompt boʻyicha birma-bir quriladi.

---

## Overview

| Item | Value |
|------|--------|
| Product | SMOXI Service |
| Type | Service Management ERP |
| Primary UI | Windows Desktop (EXE) |
| Language | Python 3.14+ |
| Desktop | PySide6 (Qt6) |
| API | FastAPI |
| ORM | SQLAlchemy 2.x |
| Local DB | SQLite |
| Cloud DB | PostgreSQL |
| Migrations | Alembic |
| Config | Pydantic Settings |
| Logging | Loguru |
| Packaging | Nuitka |
| Installer | Inno Setup |

---

## Technology Stack

- **Desktop:** PySide6 for native Windows UI
- **Backend API:** FastAPI for optional local/cloud services
- **Data access:** SQLAlchemy 2.x with Repository Pattern
- **Migrations:** Alembic (`database/migrations/`)
- **Settings:** Pydantic Settings (`app/config/`)
- **Logging:** Loguru (`app/config/logging.py`)
- **Build:** Nuitka + Inno Setup (`installer/`)

---

## Folder Explanation

```text
app/                  Application source (Clean Architecture layers)
  api/                FastAPI routers and dependencies (future)
  core/               Shared domain/core abstractions
  config/             Settings, logging, security, constants
  database/           Engine/session factories (future)
  models/             Shared SQLAlchemy models
  repositories/       Data-access abstractions
  services/           Application / domain services
  schemas/            Pydantic DTOs
  security/           Auth helpers (future)
  utils/              Pure utilities
  ui/                 Desktop shell / navigation (future)
  widgets/            Reusable Qt widgets
  modules/            Feature modules (auth, inventory, …)
  reports/            Reporting engines (future)
  telegram/           Telegram integrations (future)
  ai/                 AI assistants (future)
  automation/         Background jobs / workflows (future)
  localization/       i18n helpers
  resources/          App-packaged resources

assets/               Static assets (icons, fonts, styles, translations)
backups/              Runtime backups (ignored by git except .gitkeep)
config/               External / deploy configuration files
database/             SQLite files, PostgreSQL notes, Alembic, seeds
docs/                 Architecture and product documentation
installer/            Inno Setup scripts and packaging artifacts
logs/                 Rotating application logs
requirements/         Split dependency sets
scripts/              DevOps / maintenance scripts
tests/                Automated tests
uploads/              User uploads (runtime)
```

Each feature under `app/modules/<name>/` already includes:

`views/`, `controllers/`, `services/`, `repositories/`, `models/`, `schemas/`, `resources/`

---

## Installation

### Prerequisites

- Windows 10/11
- Python **3.14+**
- Git

### Setup

```powershell
cd "D:\Projekt\SMOXI Service"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements/dev.txt
```

For desktop-only:

```powershell
pip install -r requirements/desktop.txt
```

For server/API-only:

```powershell
pip install -r requirements/server.txt
```

### Run (foundation bootstrap)

```powershell
python main.py
# or
python run.py
```

At this phase, the entry points only bootstrap configuration and logging.

---

## Development Rules

The complete, mandatory rule set is defined in:

**[docs/EngineeringStandards.md](docs/EngineeringStandards.md)**

Summary (see the full document for details):

1. **No business logic in entry points** — `main.py` / `run.py` only bootstrap.
2. **Clean Architecture** — UI → controllers → services → repositories → models.
3. **SOLID** — prefer small interfaces and constructor injection.
4. **Repository Pattern** — no SQL/ORM calls from UI or controllers.
5. **Type hints** — annotate public functions and class attributes.
6. **PEP 8 / Ruff** — keep style consistent; run `ruff check` before commits.
7. **Config via environment** — use `SMOXI_` / `SMOXI_DB_` / `SMOXI_SECURITY_` prefixes.
8. **No secrets in git** — use `.env` (ignored) for local secrets.
9. **Feature isolation** — new capabilities live under `app/modules/<feature>/`.
10. **Tests first for domain logic** — place tests under `tests/` mirroring package layout.
11. **Soft delete + audit columns** on every business table.
12. **Never show tracebacks** to end users; log details instead.

---

## Documentation

| Document | Path |
|----------|------|
| **Master Development Prompt** | [docs/MasterDevelopmentPrompt.md](docs/MasterDevelopmentPrompt.md) |
| **Biznes Tahlili & Funksional Spetsifikatsiya** | [docs/BusinessAnalysis.md](docs/BusinessAnalysis.md) |
| **Engineering Standards** | [docs/EngineeringStandards.md](docs/EngineeringStandards.md) |
| **UI/UX Blueprint** | [docs/UIUXBlueprint.md](docs/UIUXBlueprint.md) |
| Architecture | [docs/Architecture.md](docs/Architecture.md) |
| Database | [docs/Database.md](docs/Database.md) |
| API | [docs/API.md](docs/API.md) |
| Roadmap | [docs/Roadmap.md](docs/Roadmap.md) |
| Changelog | [docs/ChangeLog.md](docs/ChangeLog.md) |

---

## License

See [LICENSE](LICENSE). Proprietary — all rights reserved unless otherwise stated.
