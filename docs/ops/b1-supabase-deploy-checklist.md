# B1 / hosted Postgres pooler checklist (optional ops)

> **Note (2026-07-13):** Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) now treat **Supabase Auth** as MVP. This checklist is for **optional** Supabase (or other) **Postgres pooler** hosting — **not** an epic acceptance gate. Auth reissue: [`docs/issues/PPT-039-supabase-auth-reissue.md`](../issues/PPT-039-supabase-auth-reissue.md).

Staging/production cutover for **database hosting only** when you choose a transaction pooler. Not Supabase Auth (that is PPT-039) or RLS (B3).

Canonical pooler guidance: [PPT-031-C §2.2](../issues/PPT-031-C-supabase-decision-brief.md). Env layout: [`environments/README.md`](../../environments/README.md). API notes: [`modules/api/README.md`](../../modules/api/README.md) § B1.

## Secrets (names only — never commit values)

Store values in `environments/staging/.env` or `environments/production/.env` (gitignored). Select with `PAPITA_ENV`.

| Secret / env var          | Used by                    | Notes                                                                   |
| ------------------------- | -------------------------- | ----------------------------------------------------------------------- |
| `DATABASE_URL`            | API runtime + B1 smoke     | Transaction pooler `:6543` with `?pgbouncer=true`                       |
| `DATABASE_URL_MIGRATIONS` | Alembic / migrate job only | Direct `:5432` (`?sslmode=require`); **never** transaction pooler       |
| `JWT_SECRET_KEY`          | API auth                   | Strong secret from secrets manager (align with PPT-044 AU1 when landed) |
| `PAPITA_ENV`              | Selector                   | `staging` or `production` for B1                                        |

Optional deploy posture (soft gate for _public_ B1): CORS / docs / TrustedHost → [#89](https://github.com/Elmorralito/save-ma-money/issues/89) (PPT-044).

**Do not require** `SUPABASE_URL` / `SUPABASE_ANON_KEY` for MVP (local JWT on B0/B1).

## Pre-deploy

1. Apply migrations with the **direct** URL:

   ```bash
   cp environments/staging/.env.example environments/staging/.env   # once
   set -a && source environments/staging/.env && set +a
   /bin/bash ./deploy/alembic.sh upgrade --env staging --url "$DATABASE_URL_MIGRATIONS"
   ```

2. Configure the API process with `PAPITA_ENV=staging` (or `production`) so Settings loads the pooler `DATABASE_URL` + `JWT_SECRET_KEY`.

3. Confirm SQLAlchemy pool opts (PPT-039): `pool_pre_ping=True`, `pool_size=DATABASE_POOL_SIZE` (default 5); on pooler URLs `max_overflow=0`. Escape hatch: `NullPool` if PgBouncer timeouts appear under load.

## Smoke

```bash
PAPITA_ENV=staging make b1-smoke
# equivalent: /bin/bash ./deploy/b1_smoke.sh --env staging
```

`make b1-smoke` **fails with a clear message** if `environments/staging/.env` is missing, points at local Docker (B0), or the pooler rejects `SELECT 1`. Plain `pytest` still **skips** when the gate fails so CI stays green without secrets ([#50](https://github.com/Elmorralito/save-ma-money/issues/50)).

## Health contract

| Probe                     | DB required | Fail surface                                       |
| ------------------------- | ----------- | -------------------------------------------------- |
| `/api/v1/health/live`     | No          | Process-only                                       |
| `/api/v1/health/ready`    | Yes         | **503** when pooler/Postgres unreachable (not 500) |
| `/api/v1/health/database` | Yes         | **503** when disconnect                            |

## Handoff to PPT-040 (#50)

CI dual-target should consume:

- Secret names: `DATABASE_URL`, `DATABASE_URL_MIGRATIONS`, `JWT_SECRET_KEY`, `PAPITA_ENV`
- Smoke entrypoint: `make b1-smoke` / `deploy/b1_smoke.sh` (default `PAPITA_ENV=staging`)
- Migrate job must use `DATABASE_URL_MIGRATIONS`, not the pooler URL

Attach redacted B1 ready/smoke logs on the closing PR for gate G7 — no passwords or full connection strings in artifacts.
