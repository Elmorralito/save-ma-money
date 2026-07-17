# Environments — Papita / save-ma-money

All runtime secrets and Compose variables live under **`environments/<name>/`**. Pick one active environment; do not scatter `.env` files under `modules/` or `docker/`.

## Names

| Folder       | Database                           | Auth (MVP)                                                    | Typical use                       |
| ------------ | ---------------------------------- | ------------------------------------------------------------- | --------------------------------- |
| `local`      | B0 Docker Postgres                 | Supabase Auth (or transitional local JWT until PPT-039 lands) | Day-to-day host uvicorn + Compose |
| `staging`    | Any Postgres URL (pooler optional) | Supabase Auth                                                 | Staging                           |
| `production` | Any Postgres URL (pooler optional) | Supabase Auth                                                 | Production (tighter CORS)         |

**Epic direction (2026-07-13):** Supabase is **Auth-only** for MVP ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)). Supabase-hosted Postgres is optional — see [`docs/issues/PPT-039-supabase-auth-reissue.md`](../docs/issues/PPT-039-supabase-auth-reissue.md).

## Selecting the active environment

**Parameter:** `PAPITA_ENV` (default **`local`**).

```bash
export PAPITA_ENV=local          # API Settings, default Alembic/Compose
export PAPITA_ENV=staging        # staging secrets / optional pooler smoke
```

Deploy scripts also accept `--env <name>`:

```bash
./deploy/alembic.sh upgrade --env local
PAPITA_ENV=local make auth-smoke     # Auth DoD (JWT → /auth/me + accounts)
PAPITA_ENV=staging make b1-smoke     # optional pooler connectivity; not Auth DoD
```

Compose:

```bash
# Full stack (Postgres + Redis + API). Redis is enabled for the API container by default.
docker compose --env-file environments/local/.env -f docker/docker-compose.yml up --build
# Or: make stack-up

# Postgres + Redis only (host uvicorn)
docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d
# Or: make redis-up   # Redis service only

make redis-smoke   # GET /health/ready + /health/redis against a running API
```

### Redis (PPT-043)

| Context                      | `REDIS_URL`                        | Notes                                                   |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------- |
| Compose `api` service        | `redis://redis:6379/0` (hardcoded) | `REDIS_ENABLED` / rate-limit default **true**           |
| Host uvicorn + Compose Redis | `redis://localhost:6379/0`         | Set in `environments/local/.env`                        |
| Staging / production         | Managed `rediss://…`               | Placeholders in `staging` / `production` `.env.example` |

Config file: [`docker/redis/redis.conf`](../docker/redis/redis.conf) (AOF, 256mb maxmemory, allkeys-lru).

## Setup

```bash
cp environments/local/.env.example environments/local/.env
# edit JWT / DATABASE_URL / DB_* ; add SUPABASE_URL when wiring Auth (PPT-039)

cp environments/staging/.env.example environments/staging/.env
# fill Auth + optional pooler / migrations URLs (never commit)
```

- Commit only `*.env.example` and this README.
- Real `.env` files are gitignored (`environments/**/.env`).
- `AUTH_PROVIDER` — omit or set `supabase` when `SUPABASE_URL` is set (auto); use `local` only for HS256 tests. Register/login call Supabase Auth `sign_up` / `sign_in_with_password`.
- Decision brief (+ G7 supersede): [`docs/issues/PPT-031-C-supabase-decision-brief.md`](../docs/issues/PPT-031-C-supabase-decision-brief.md)
- Optional pooler checklist: [`docs/ops/b1-supabase-deploy-checklist.md`](../docs/ops/b1-supabase-deploy-checklist.md)
