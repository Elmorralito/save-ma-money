---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Soft-delete / categories / refresh_balances / API bounds / report SQL PRs
- PR-5…PR-7 + efficiency PR-A…F committed (`8174dab`)
- PPT-044 brief + `docs/ops` checklists folded into `docs/design/` Part VIII / § Ops;
  removed `docs/ops/` directory (SSOT is design README + Part VIII)

### Next action

- Open/push PR for branch `docs/create-issue-skill` (create-issue skill + PPT-044 + efficiency)
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Redis optional by default (`REDIS_ENABLED=false`)
