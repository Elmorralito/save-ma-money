---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Model soft-delete / categories / refresh_balances PRs committed
- PR-4: trends window always; extension forbid/bounds; search cap; Auth allowlist
- Remaining PPT-044 transport/client-contract work may still be uncommitted

### Next action

- PR-5: SQL-windowed report loads + account-scoped transfer cash-flow direction
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
