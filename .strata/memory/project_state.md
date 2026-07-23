---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Model soft-delete PR-1: `get_records`/`count_records` active-only by default;
  `upsert_record` blocks revival unless `reactivate=True`; users auth lookups
  use `include_deleted` for collision / subject bans
- PPT-044 API hardening + client-contract work still uncommitted locally (API/env)

### Next action

- PR-2 categories: require `owner=` on service ops; reject global delete/update
- Then PR-3 `refresh_balances` defaults False on writes/cash_flow
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
- Large PPT-044 API diff still WIP alongside model hardening commits
