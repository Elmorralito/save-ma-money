---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Model soft-delete PR-1 committed
- Model categories PR-2 committed
- PR-3: `refresh_balances` default False on txn writes + cash_flow; API refreshes
  MVs once after ledger mutations
- PPT-044 API hardening + client-contract work still uncommitted locally

### Next action

- PR-4 API: trends window always; extension forbid/bounds; search cap; Auth
  error allowlist
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
- Large PPT-044 API diff still WIP alongside model hardening commits
