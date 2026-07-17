---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-043 PR #94: QC green after REDIS_URL test fix; Codecov patch ~95%
- Added owner-id-none cache BYPASS + Settings Redis URL + health degraded tests

### Next action

- Confirm `codecov/patch` ≥ ~97.7% on #94
- Staging: managed `REDIS_URL` when enabling horizontal scale
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
