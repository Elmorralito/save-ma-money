# B1 / hosted Postgres pooler checklist (optional ops)

> **Note (2026-07-13):** Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) treat **Supabase Auth** as MVP. This checklist is for **optional** Supabase (or other) **Postgres pooler** hosting — **not** an epic acceptance gate. Auth reissue: [`docs/issues/PPT-039-supabase-auth-reissue.md`](../issues/PPT-039-supabase-auth-reissue.md). Auth smoke: `make auth-smoke`.

Staging/production cutover for **database hosting only** when you choose a transaction pooler. Not Supabase Auth (PPT-039) or RLS (B3).

Canonical pooler guidance: [PPT-031-C §2.2](../issues/PPT-031-C-supabase-decision-brief.md). Env layout: [`environments/README.md`](../../environments/README.md). API notes: [`modules/api/README.md`](../../modules/api/README.md) § B1.

## Secrets (names only — never commit values)

Store values in `environments/staging/.env` or `environments/production/.env` (gitignored). Select with `PAPITA_ENV`.

| Secret / env var               | Used by                | Notes                                                                     |
| ------------------------------ | ---------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`                 | API runtime + B1 smoke | Transaction pooler `:6543` with `?pgbouncer=true`                         |
| `DATABASE_URL_MIGRATIONS`      | Alembic / migrate only | Direct `:5432` (`?sslmode=require`); **never** transaction pooler         |
| `AUTH_PROVIDER` / `SUPABASE_*` | Auth (PPT-039)         | Prefer `make auth-smoke` — not required solely for pooler DB connectivity |
| `PAPITA_ENV`                   | Selector               | `staging` or `production` for B1                                          |

Optional deploy posture (soft gate for _public_ B1): CORS / docs / TrustedHost → [#89](https://github.com/Elmorralito/save-ma-money/issues/89) (PPT-044).

**Auth MVP** uses `SUPABASE_URL` (+ optional anon key). Pooler DB hosting does **not** require Auth secrets.

## Pre-deploy

1. Apply migrations with the **direct** URL:

   ```bash
   cp environments/staging/.env.example environments/staging/.env   # once
   set -a && source environments/staging/.env && set +a
   /bin/bash ./deploy/alembic.sh upgrade --env staging --url "$DATABASE_URL_MIGRATIONS"
   ```

2. Configure the API process with `PAPITA_ENV=staging` (or `production`) so Settings loads the pooler `DATABASE_URL` (Auth via `AUTH_PROVIDER=supabase`).

3. Confirm SQLAlchemy pool opts (optional): `pool_pre_ping=True`, `pool_size=DATABASE_POOL_SIZE` (default 5); on pooler URLs `max_overflow=0`. Escape hatch: `NullPool` if PgBouncer timeouts appear under load.

## Smoke

```bash
# Auth DoD (PPT-039)
PAPITA_ENV=local make auth-smoke

# Optional pooler DB only
PAPITA_ENV=staging make b1-smoke
# equivalent: /bin/bash ./deploy/b1_smoke.sh --env staging
```

`make b1-smoke` **fails with a clear message** if `environments/staging/.env` is missing, points at local Docker (B0), or the pooler rejects `SELECT 1`. Plain `pytest` still **skips** when the gate fails. This path is **parked optional ops** — [#50](https://github.com/Elmorralito/save-ma-money/issues/50) / epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) do **not** require Supabase-hosted Postgres (Auth-first: Supabase = users/Auth/tokens only).

## Health contract

| Probe                     | DB required | Fail surface                                       |
| ------------------------- | ----------- | -------------------------------------------------- |
| `/api/v1/health/live`     | No          | Process-only                                       |
| `/api/v1/health/ready`    | Yes         | **503** when pooler/Postgres unreachable (not 500) |
| `/api/v1/health/database` | Yes         | **503** when disconnect                            |

## Handoff to PPT-040 (#50)

CI dual-target should consume:

- Auth: `SUPABASE_URL` (+ JWKS / anon for smoke), `AUTH_PROVIDER=supabase`
- DB: `DATABASE_URL` (any Postgres), optional `DATABASE_URL_MIGRATIONS` for migrate jobs
- Smoke entrypoints: `make auth-smoke` (Auth DoD); `make b1-smoke` (optional pooler)
- Migrate job must use `DATABASE_URL_MIGRATIONS`, not the pooler URL

Attach redacted ready/Auth-smoke logs on the closing PR — no passwords or full connection strings in artifacts.
