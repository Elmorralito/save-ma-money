---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-043 Redis on PR #94; added Codecov patch-gap tests
- CI fix: rate-limiter tests must set `REDIS_URL` when `REDIS_ENABLED=true`
  (Settings model_validator); local `.env` masked the failure

### Next action

- Confirm `quality-control` + `codecov/patch` green on #94
- Staging: managed `REDIS_URL` when enabling horizontal scale
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
