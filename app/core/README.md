# Platform Core

SMOXI Service platform core: ORM base mixins, database engine/session, Unit of Work, DI container, audit logging, exceptions.

## Dependencies

- SQLAlchemy 2.x
- Pydantic Settings
- Loguru

## Public API

- `app.core.container.ServiceContainer`
- `app.models.base.Base`, `AuditMixin`
- `app.database.unit_of_work.UnitOfWork`
- `app.repositories.base.BaseRepository`
- `app.services.audit_service.AuditService`

## Change History

| Version | Date | Change |
|---------|------|--------|
| 0.6.0 | 2026-07-23 | Initial platform core implementation |
