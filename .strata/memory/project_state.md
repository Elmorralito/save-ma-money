---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-043 Redis on PR #94; Codecov patch was ~74% (target ~97.7% auto)
- Added API unit/route tests for patch gaps: idempotency, redis client, cache
  fail-open, broker, rate-limit edges, session store, transactions/reports Redis
- Local: `modules/api/tests` — 242 passed, 21 skipped (live DB / B1 / Auth smoke)

### Next action

- Push coverage commit; confirm `codecov/patch` green on #94
- Staging: managed `REDIS_URL` when enabling horizontal scale
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
