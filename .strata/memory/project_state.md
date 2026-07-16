---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

Compose API now injects `AUTH_PROVIDER` / `SUPABASE_*`. Smoke needs a real email
(`AUTH_SMOKE_EMAIL`) and Confirm email off (or custom SMTP) for local.

### Last completed (this session)

- PPT-040 PR [#92](https://github.com/Elmorralito/save-ma-money/pull/92): B0 live txn/movement tests,
  Auth-first docs, source-package Codecov measurement
- Diagnosed `codecov/patch` fail: suite mutates class-level `LinkedEntity.other_entity_service`,
  hiding isinstance-continue; tests now clone unloaded links + ternary resolve/fallback

### Next action

- Commit + push Codecov isolation fix on `test/PPT-050` → confirm `codecov/patch` green on #92
- Merge #92 → close #50; optional `make auth-smoke` against staging Auth
- Do not reintroduce local password JWT as default; do not gate on Supabase PG/pooler

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Pending: `extends.py` + `test_linked_entities_get.py` + this strata update
