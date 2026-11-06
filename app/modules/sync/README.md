# Sync

Offline-first cloud sync foundation.

## API

- `SyncService.pull(company_id)` — pending/conflict/failed entities
- `SyncService.push_acks(company_id, acks)` — mark synced / conflict
- `SyncService.count_pending(company_id)`

HTTP: `GET /api/v1/sync/pull`, `POST /api/v1/sync/push`

## Oʻzgarishlar

| Versiya | Sana | Izoh |
|---------|------|------|
| 1.0.0 | 2026-07-24 | Pull/push ack kontrakti (WO + Customer) |
