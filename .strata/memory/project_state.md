---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-043 transactions Redis:
  - Short-TTL cache on `GET /transactions` list + detail (`transactions` namespace, 30s)
  - Ledger writes invalidate `transactions` + `reports` + `accounts`
  - `Idempotency-Key` on `POST /transactions` and `/bulk` (`core/idempotency.py`)

### Next action

- Optional: tenant-scoped API rate limits (Free/Pro tiers)
- Staging: managed `REDIS_URL` when enabling horizontal scale
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
