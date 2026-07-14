---
name: save-ma-money State
description: Compose API injects SUPABASE_*; Auth smoke needs real email domain.
---

## WHERE WE LEFT OFF (current)

Docker API lacked `AUTH_PROVIDER` / `SUPABASE_*`, so registers wrote only to local
Postgres. Compose now injects Auth env. Supabase rejects `.local` / `example.com`
and rate-limits default SMTP — set `AUTH_SMOKE_EMAIL` and disable Confirm email.

### Last completed (this session)

- `docker-compose.yml` passes Supabase Auth settings into `api`
- Auth smoke requires `AUTH_SMOKE_EMAIL` or `AUTH_SMOKE_EMAIL_DOMAIN`

### Next action

- Add `AUTH_SMOKE_EMAIL=you+smoke@yourdomain.com` to `environments/local/.env`
- Auth → Email → disable Confirm email (local)
- `make auth-smoke` and confirm user appears in Supabase Auth dashboard

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
