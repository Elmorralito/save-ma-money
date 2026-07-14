---
name: save-ma-money State
description: Register/login use supabase-py Auth; JWKS verify on protected routes.
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** `/auth/register` and `/auth/login` call Supabase Auth
(`sign_up` / `sign_in_with_password`). `SUPABASE_URL` auto-selects `AUTH_PROVIDER=supabase`.

### Last completed (this session)

- `supabase` dependency + `core/supabase_auth.py` client helpers
- Router wires Auth module; local HS256 kept for unit tests
- Env example Auth-first under `environments/local/`

### Next action

- Ensure local `.env` has `SUPABASE_URL` + `SUPABASE_ANON_KEY` (no `AUTH_PROVIDER=local`)
- Run API + `make auth-smoke`
- Open PR `ops/PPT-039` → `main`

### Prerequisites

- Supabase Auth email/password enabled (disable confirm email for local smoke if needed)

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
