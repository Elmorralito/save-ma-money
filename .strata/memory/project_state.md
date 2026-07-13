---
name: save-ma-money State
description: PPT-039 Supabase Auth impl on ops/PPT-039; G5/Part VI + auth-smoke.
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** Auth runtime (JWKS, provision, pass-through) on `ops/PPT-039`.
Follow-on: G5/Part VI rewrite, `make auth-smoke`, issue checklist sync.

### Last completed (this session)

- `AUTH_PROVIDER=supabase` JWKS + `ensure_from_auth_subject`
- Part VI / `PPT-031-auth-contract.md` G5 supersede
- `deploy/auth_smoke.sh` + `make auth-smoke`

### Next action

- Set `AUTH_PROVIDER=supabase` in local/staging `.env` (keys already optional)
- Run `make auth-smoke` against a live API
- PR `ops/PPT-039` → `main`; wire #50 CI secrets to Auth smoke

### Prerequisites

- `export PAPITA_ENV=local`
- Supabase Auth project (`SUPABASE_URL`, `SUPABASE_ANON_KEY` for pass-through)

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
