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

- Supabase Auth client register/login + JWKS verify
- Compose Auth env wiring; smoke email guidance
- Learning: `learnings/supabase-auth-ownership.md`

### Next action

- Set `AUTH_SMOKE_EMAIL` in `environments/local/.env`
- Disable Confirm email (local) → `make auth-smoke` → users appear in Supabase Auth
- Do not reintroduce local password JWT as default

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
