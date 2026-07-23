---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Model soft-delete PR-1 committed (`fix(model): exclude soft-deleted…`)
- Model categories PR-2: `CategoriesService` always requires `owner=`; reject
  global create/update/delete (seed `owner_id IS NULL` rows)
- PPT-044 API hardening + client-contract work still uncommitted locally (API/env)

### Next action

- Commit PR-2 categories if desired; then PR-3 `refresh_balances` defaults False
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
- Large PPT-044 API diff still WIP alongside model hardening commits
