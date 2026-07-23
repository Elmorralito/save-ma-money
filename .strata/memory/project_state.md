---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Soft-delete / categories / refresh_balances / API bounds / report SQL PRs
- PR-5: SQL-windowed report loads + account-scoped transfer cash-flow direction
- PR-6 (in progress / local): DB pagination for accounts/categories; idempotency body digest
- Remaining PPT-044 transport/client-contract work may still be uncommitted

### Next action

- Finish/verify PR-6 tests; then PR-7 (RL coverage + TrustedHost in prod)
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
