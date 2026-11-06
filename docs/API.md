# SMOXI Service HTTP API

**Versiya:** `/api/v1`
**OpenAPI:** `http://127.0.0.1:8787/api/docs`
**Ishga tushirish:** `pwsh -File scripts/run_api.ps1` yoki `python -m app.api.server`

## Auth

| Method | Path | Izoh |
|--------|------|------|
| POST | `/api/v1/auth/login` | `{company_code, username, password}` → Bearer token |
| GET | `/api/v1/auth/me` | Joriy foydalanuvchi |

Header: `Authorization: Bearer <token>`

## Resources

| Method | Path |
|--------|------|
| GET | `/api/v1/health` |
| GET | `/api/v1/work-orders?status=&q=&limit=` |
| GET | `/api/v1/customers?q=` |
| GET | `/api/v1/sync/pull?since=&limit=` |
| POST | `/api/v1/sync/push` | `{acks:[{entity_type,uuid,version,status}]}` |
| GET | `/api/v1/sync/pending-count` |

## Sync modeli

- Entity `sync_status`: `pending` · `synced` · `conflict` · `failed`
- Optimistic lock: `version` mos kelmasa → `conflict`
- Hozirgi entitylar: `work_order`, `customer`

## Xatoliklar

```json
{"error":{"code":"validation_error","message":"…","details":…}}
```

Desktop va API **bir xil** service/repository qatlamini ulashadi.
