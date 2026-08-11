# Environments — Papita / save-ma-money

All runtime secrets and Compose variables live under **`environments/<name>/`**. Pick one active environment; do not scatter `.env` files under `modules/` or `docker/`.

## Names

| Folder       | Database                           | Auth (MVP)                                                    | Typical use                            |
| ------------ | ---------------------------------- | ------------------------------------------------------------- | -------------------------------------- |
| `local`      | B0 Docker Postgres                 | Supabase Auth (MVP); `AUTH_PROVIDER=local` for B0 pytest only | Day-to-day Compose API (`make api-up`) |
| `staging`    | Any Postgres URL (pooler optional) | Supabase Auth                                                 | Staging                                |
| `production` | Any Postgres URL (pooler optional) | Supabase Auth                                                 | Production (tighter CORS)              |

**Epic direction (2026-07-13):** Supabase is **Auth-only** for MVP ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)). Supabase-hosted Postgres is optional — see [`docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49`](../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49).

## Selecting the active environment

**Parameter:** `PAPITA_ENV` (default **`local`**).

```bash
export PAPITA_ENV=local          # API Settings, default Alembic/Compose
export PAPITA_ENV=staging        # staging secrets / optional pooler smoke
```

Deploy scripts also accept `--env <name>`:

```bash
./bin/bash/alembic.sh upgrade --env local
PAPITA_ENV=local make auth-smoke     # Auth DoD (JWT → /auth/me + accounts)
PAPITA_ENV=staging make b1-smoke     # optional pooler connectivity; not Auth DoD
```

Compose API (PPT-045) — uvicorn runs **in the API container**:

```bash
# Canonical: api + Postgres + Redis + migrate (uvicorn via Dockerfile CMD)
make api-up
# Or full explicit stack: make stack-up

make redis-smoke      # GET /health/ready + /health/redis against the API container
```

### Uvicorn bind vs Settings vs Compose publish

| Variable / flag          | Where                                | Role                                                                         |
| ------------------------ | ------------------------------------ | ---------------------------------------------------------------------------- |
| Compose image `CMD`      | `docker/api/Dockerfile`              | Actual uvicorn bind: literal `0.0.0.0:8000` (no `--reload`)                  |
| Settings `HOST` / `PORT` | `environments/<env>/.env` (optional) | **Unused for bind** (compat only); Compose `CMD` is SSOT                     |
| `API_PORT`               | Compose `.env`                       | Host→container **publish** map (`${API_PORT}:8000`), not in-container listen |

Do not pass `--workers` on B0 without Redis rate limits (`REDIS_RATE_LIMIT_ENABLED=true`). See [`modules/api/README.md`](../modules/api/README.md) § Workers vs Redis.

### Redis (PPT-043)

| Context                       | `REDIS_URL`                        | Notes                                                           |
| ----------------------------- | ---------------------------------- | --------------------------------------------------------------- |
| Compose `api` service         | `redis://redis:6379/0` (hardcoded) | Used by `make api-up` / `stack-up`; rate-limit default **true** |
| Host tooling vs Compose Redis | `redis://localhost:6379/0`         | Only for host-side clients; API container never uses this       |
| Staging / production          | Managed `rediss://…`               | Placeholders in `staging` / `production` `.env.example`         |

Config file: [`docker/redis/redis.conf`](../docker/redis/redis.conf) (AOF, 256mb maxmemory, allkeys-lru).

## Setup

```bash
cp environments/local/.env.example environments/local/.env
# set DATABASE_URL / DB_* ; for day-to-day Auth set SUPABASE_URL + SUPABASE_ANON_KEY (PPT-039 landed)

cp environments/staging/.env.example environments/staging/.env
# fill Auth + optional pooler / migrations URLs (never commit)
```

- Commit only `*.env.example` and this README.
- Real `.env` files are gitignored (`environments/**/.env`).
- `AUTH_PROVIDER` — omit or set `supabase` when `SUPABASE_URL` is set (auto); use `local` only for HS256 tests/CI. Register/login call Supabase Auth `sign_up` / `sign_in_with_password`.
- API package docs: [`modules/api/README.md`](../modules/api/README.md)
- Auth reissue: [`docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49`](../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49)
- Decision brief (+ G7 supersede): [`docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31`](../docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31)
- Optional pooler checklist: [`docs/ops/b1-supabase-deploy-checklist.md`](../docs/ops/b1-supabase-deploy-checklist.md)
