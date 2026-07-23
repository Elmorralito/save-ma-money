---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Soft-delete / categories / refresh_balances / API bounds / report SQL PRs
- PR-5…PR-6: report SQL loads; list pagination; idempotency body digests
- PR-7 + efficiency PR-A…F: RL/TrustedHost glue; PENDING MV skip; account re-fetch
  cuts; cache version reuse; page-scoped balances; Redis limiter app-state + txn DI
  cache; page+total lists; spending SQL agg; bulk FK prefetch

### Next action

- Push/open PR for hardening + efficiency follow-ups when ready
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
