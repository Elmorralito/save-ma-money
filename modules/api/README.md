# Papita Transactions API

FastAPI package (`papita-txnsapi`) for the **save-ma-money** monorepo. It exposes a versioned REST surface over [`papita-txnsmodel`](../model/README.md), which owns SQLModel schemas, migrations, repositories, services, and ingestion handlers. **Business rules live in the model layer** — API routers validate HTTP shapes, resolve tenant context from JWT, and delegate to existing services.

This document is the **single API reference**: architecture, integration patterns, v3 data shapes, and the full endpoint catalog (formerly split across `API_Endpoints.md.md`, `API_Documentation.md.md`, and `README.md - Project Structure.md`).

**Table of contents**

1. [Overview](#overview)
2. [Status and roadmap](#status-and-roadmap)
3. [Architecture](#architecture)
4. [Package layout](#package-layout)
5. [Model layer integration](#model-layer-integration)
6. [Stack and local setup](#stack-and-local-setup)
7. [Integration guide](#integration-guide)
8. [Endpoint reference](#endpoint-reference)
9. [Related documentation](#related-documentation)

---

## Overview

The API manages personal finance data aligned to the **v3 PostgreSQL schema** (`papita_transactions`): accounts with kind-specific extensions, hierarchical categories, posted transactions and transfers, and read-only reports. JSON over HTTPS; JWT bearer auth for protected routes.

| Topic                   | Value                                                                                                                                                                       |
| :---------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API version             | `v1`                                                                                                                                                                        |
| Base URL (dev)          | `http://localhost:8000/api/v1`                                                                                                                                              |
| Base URL (prod)         | `https://api.savemamoney.com/api/v1`                                                                                                                                        |
| OpenAPI (when deployed) | `/api/openapi.json`                                                                                                                                                         |
| Database                | PostgreSQL only — Docker locally (B0); any hosted Postgres in staging/prod (Supabase PG optional)                                                                           |
| Auth                    | **Supabase Auth** (PPT-039 / [#49](https://github.com/Elmorralito/save-ma-money/issues/49)); `AUTH_PROVIDER=local` HS256 for B0 tests only                                  |
| Design program          | PPT-031 closed ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)); implementation epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) |

### v3 alignment at a glance

| Resource                                 | v3 backing                                                                                                                                                                 | MVP |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-- |
| `/categories/*`                          | `categories` (income/expense taxonomy)                                                                                                                                     | Yes |
| `/accounts/*`                            | `accounts` + extension tables; `balance` from `account_balances` MV                                                                                                        | Yes |
| `/transactions/*`                        | `transactions` (`transaction_kind`: INCOME, EXPENSE, TRANSFER)                                                                                                             | Yes |
| `/movements/*`                           | **Alias** — same rows where `transaction_kind = TRANSFER`                                                                                                                  | Yes |
| `/reports/*` (except budget-performance) | `ReportService` aggregations over ledger + categories                                                                                                                      | Yes |
| `/budgets/*`                             | Deferred — v4.1 ([`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a)) | 501 |
| `/auth/refresh`, `/auth/logout`          | **Supabase:** implemented (session rotate / sign-out + optional Redis denylist). **Local HS256:** 501                                                                      | —   |
| `/bff/auth/*`                            | PPT-049 browser BFF: HttpOnly `papita_sid` session cookie; JWTs server-side; CSRF `X-Papita-CSRF`. Coexists with Bearer `/auth/*` (`make auth-smoke`)                      | Yes |
| `/transactions/{id}/split`               | Deferred — v4 `transaction_splits`                                                                                                                                         | 501 |

**Enum convention:** API JSON uses lowercase slugs (`expense`, `checking`); PostgreSQL stores uppercase enums (`EXPENSE`, `CHECKING`).

**Dependencies:** `python-multipart` is present (OAuth2 form login).

Further mapping: [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) · schema: [`docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../../docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32) · model detail: [`modules/model/README.md`](../model/README.md).

---

## Status and roadmap

**Current tree (2026-07-17):** runnable FastAPI MVP — all PPT-032 child issues **#43–#50** and prerequisite **#51** are **closed**. Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) remains open for formal close-out only. OpenAPI at `/api/openapi.json` is the runtime contract; this README is the human catalog.

| Child   | Issue                                                         | Delivered                                                                                                         |
| :------ | :------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------- |
| PPT-033 | [#43](https://github.com/Elmorralito/save-ma-money/issues/43) | Spec ↔ v3 validation; [coverage matrix](../../docs/design/ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43) |
| PPT-034 | [#45](https://github.com/Elmorralito/save-ma-money/issues/45) | App scaffold, middleware, health probes                                                                           |
| PPT-035 | [#44](https://github.com/Elmorralito/save-ma-money/issues/44) | Auth routes + tenant (`get_current_owner`)                                                                        |
| PPT-036 | [#46](https://github.com/Elmorralito/save-ma-money/issues/46) | Accounts + categories CRUD                                                                                        |
| PPT-037 | [#47](https://github.com/Elmorralito/save-ma-money/issues/47) | Transactions + movements TRANSFER alias                                                                           |
| PPT-038 | [#48](https://github.com/Elmorralito/save-ma-money/issues/48) | Reports (spending, cash-flow, trends, export)                                                                     |
| PPT-039 | [#49](https://github.com/Elmorralito/save-ma-money/issues/49) | Supabase Auth (JWKS); local HS256 = tests                                                                         |
| PPT-040 | [#50](https://github.com/Elmorralito/save-ma-money/issues/50) | Integration tests + B0 CI (Auth-first)                                                                            |
| PPT-041 | [#51](https://github.com/Elmorralito/save-ma-money/issues/51) | Model hardening (prerequisite)                                                                                    |

| Implemented    | Location                                                                                      |
| :------------- | :-------------------------------------------------------------------------------------------- |
| FastAPI app    | `src/papita_txnsapi/main.py` — lifespan, CORS, logging, exception handlers                    |
| Settings / env | `src/papita_txnsapi/config/settings.py`, `config/environment.py`                              |
| Auth / JWT     | `core/security.py`, `core/supabase_auth.py` — JWKS (`supabase`) or HS256 (`local`)            |
| Health         | `routers/v1/health.py` — `/`, `/ready`, `/live`, `/database`, `/auth`, `/redis`               |
| Auth           | `routers/v1/auth.py` — register, login, `/me`, OAuth/SSO, refresh/logout (Supabase)           |
| Accounts       | `routers/v1/accounts.py`                                                                      |
| Categories     | `routers/v1/categories.py`                                                                    |
| Transactions   | `routers/v1/transactions.py` — bulk; split → 501                                              |
| Movements      | `routers/v1/movements.py` — TRANSFER alias + execute                                          |
| Reports        | `routers/v1/reports.py` — budget-performance → 501                                            |
| Deferred 501   | `routers/v1/budgets.py`; split; budget-performance; refresh/logout when `AUTH_PROVIDER=local` |
| Schemas / deps | `schemas/*`, `dependencies/auth.py`, `pagination.py`, `services.py`, `tenant.py`              |
| Tests          | `modules/api/tests/` — unit + B0 live-DB; Auth mock + `make auth-smoke`                       |

| Remaining (post-MVP / epic hygiene) | Track via                                                                                                                                                                                                           |
| :---------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Formal epic #42 close               | Maintainer AC on [#42](https://github.com/Elmorralito/save-ma-money/issues/42)                                                                                                                                      |
| Redis / rate-limit / packaging      | [#83](https://github.com/Elmorralito/save-ma-money/issues/83) PPT-043, [#89](https://github.com/Elmorralito/save-ma-money/issues/89) PPT-044, [#93](https://github.com/Elmorralito/save-ma-money/issues/93) PPT-045 |

**Model readiness (PPT-041):** closed — routers call `papita-txnsmodel` services only (no duplicate business logic).

**MVP scope:** **32** catalog endpoints (health, auth register/login, accounts, categories, transactions, movements, four reports). Deferred 501: budgets, transaction split, budget-performance; refresh/logout only when `AUTH_PROVIDER=local`.

---

## Architecture

```mermaid
flowchart TB
  subgraph clients [Clients]
    WEB[Web / mobile / scripts]
  end

  subgraph api [papita_txnsapi]
    R[routers/v1/]
    SCH[schemas/]
    DEP[dependencies/]
    SEC[core/security.py]
  end

  subgraph model [papita_txnsmodel — implemented]
    SV[services/]
    RP[repositories/]
    DBT[(PostgreSQL papita_transactions)]
  end

  WEB --> R
  R --> DEP --> SEC
  R --> SCH
  R --> SV
  SV --> RP --> DBT
```

| Layer            | Package                        | Responsibility                                                |
| :--------------- | :----------------------------- | :------------------------------------------------------------ |
| **Routers**      | `papita_txnsapi/routers/`      | HTTP paths, status codes, OpenAPI tags                        |
| **Schemas**      | `papita_txnsapi/schemas/`      | Request/response Pydantic models — **no business validators** |
| **Dependencies** | `papita_txnsapi/dependencies/` | JWT → `UsersDTO`, pagination, service factories               |
| **Services**     | `papita_txnsmodel/services/`   | Business rules, DTO validation, MV refresh                    |
| **Repositories** | `papita_txnsmodel/access/`     | SQL, soft delete, tenant filters                              |

**FR-17:** OpenAPI at `/api/openapi.json` is the runtime contract. This README is the human-readable catalog and integration guide (former `API_Endpoints.md.md` / `API_Documentation.md.md` merged here).

---

## Package layout

```
modules/api/
├── pyproject.toml
├── README.md                          # this file (canonical API reference)
├── tests/                             # unit + B0 live-DB + Auth smoke helpers
└── src/papita_txnsapi/
    ├── main.py                        # create_app, lifespan, ASGI app
    ├── config/                        # settings, environment, logger.yaml
    ├── core/                          # security, supabase_auth, db/redis health, rate limit
    ├── dependencies/                  # auth, pagination, services, tenant, redis
    ├── middleware/                    # request logging
    ├── schemas/                       # auth, accounts, categories, transactions, movements, reports, …
    └── routers/v1/                    # health, auth, accounts, categories, transactions, movements, reports, budgets
```

Monorepo migrations live under [`modules/model/alembic/`](../model/README.md#database-migrations), not in the API package.

---

## Model layer integration

Routers **must not** embed SQL or duplicate DTO validation. Use model services with `owner=UsersDTO` resolved from JWT `sub`.

| API area                | Model service         | Notes                                                              |
| :---------------------- | :-------------------- | :----------------------------------------------------------------- |
| Register / login        | `UsersService`        | `ensure_password_manager()` in app lifespan (NFR-08)               |
| Accounts CRUD + balance | `AccountsService`     | `create_account`, `get_with_extension`, `get_balance`              |
| Categories CRUD         | `CategoriesService`   | Blocks writes to global categories                                 |
| Transactions            | `TransactionsService` | INCOME/EXPENSE; refreshes balance MVs on write                     |
| Movements (transfers)   | `TransactionsService` | `list_transfers`, `create_transfer`, `complete_transfer`, `cancel` |
| Reports                 | `ReportService`       | `spending`, `cash_flow`, `trends`, `export`                        |

**Tenant flow:** `Authorization: Bearer` → decode JWT → `UsersService.get_owner(sub)` → pass `owner=` to every financial service call.

**Database:** `Settings` loads `DATABASE_URL` from `environments/$PAPITA_ENV/.env` (see [`environments/README.md`](../../environments/README.md)).

**ER diagram:** [`docs/postgres_papita_transactions_v4.png`](../../docs/postgres_papita_transactions_v4.png) (v3 core + balance materialized views).

---

## Stack and local setup

| Component         | Version / note                                                |
| :---------------- | :------------------------------------------------------------ |
| FastAPI           | `>=0.135.0,<0.140.0`                                          |
| Starlette         | `>=1.3.1,<2.0.0`                                              |
| Pydantic Settings | `>=2.13.1`                                                    |
| Auth              | Supabase JWKS (`AUTH_PROVIDER=supabase`) or local HS256 tests |
| Uvicorn           | `>=0.41.0`                                                    |
| Data layer        | `papita-transactions-model` (path dependency)                 |

```bash
# From repository root
poetry install

cp environments/local/.env.example environments/local/.env
# Prefer AUTH_PROVIDER=supabase + SUPABASE_URL (+ ANON_KEY); use AUTH_PROVIDER=local + JWT_SECRET_KEY for B0 pytest only
# DATABASE_URL (PostgreSQL URL required)
export PAPITA_ENV=local

# Migrate database
/bin/bash ./bin/alembic.sh upgrade --env local --docker-rm
```

**Canonical runtime (PPT-045):** uvicorn runs **inside Docker** via the Compose API image — not as a host Poetry process.

| Path            | Command             | Notes                                                        |
| --------------- | ------------------- | ------------------------------------------------------------ |
| API (canonical) | `make api-up`       | Builds/starts `api` + depends_on (Postgres, Redis, migrate)  |
| Full stack      | `make stack-up`     | Explicit `up` of all services in `docker/docker-compose.yml` |
| Full + health   | `make api-all`      | Same as `stack-up`, then waits for `/api/v1/health/live`     |
| Tear down       | `make api-all-down` | Compose `down` for the local project                         |

```bash
cp environments/local/.env.example environments/local/.env
make api-up
# Docs: http://localhost:8000/api/docs
# OpenAPI: http://localhost:8000/api/openapi.json
# Health: http://localhost:8000/api/v1/health/ready
# Smoke: make redis-smoke
```

In-container bind is literal `0.0.0.0:8000` ([`docker/api/Dockerfile`](../../docker/api/Dockerfile) `CMD` — no `--reload` / `--workers`). Host publish uses Compose `API_PORT` (`${API_PORT}:8000`). Settings `HOST`/`PORT` are **unused for bind** (env-file compatibility only).

| Service      | URL                                       |
| ------------ | ----------------------------------------- |
| Swagger UI   | http://localhost:8000/api/docs            |
| OpenAPI JSON | http://localhost:8000/api/openapi.json    |
| Health ready | http://localhost:8000/api/v1/health/ready |

**Web TypeScript consumers (PPT-065):** after OpenAPI-affecting API changes, refresh the committed web artifact with `make web-openapi` (offline dump — no Compose required). See [`modules/web/README.md`](../web/README.md#openapi-typegen-ci-strategy-ppt-065--130--locked-b).

The API container uses `DATABASE_URL=...@postgres-db:5435/papita` and `REDIS_URL=redis://redis:6379/0` on the Compose network. Healthcheck: `/api/v1/health/live`.

Database + Redis only (no API): `docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d` (or `make redis-up` for Redis alone).

`/health/ready` returns **200** with `{"ready": true}` when the database accepts `SELECT 1` (and Redis when `REDIS_ENABLED=true`); **503** with `{"ready": false}` when Postgres (or required Redis) is unreachable.

### Workers vs Redis (process packaging)

B0 default is a **single** uvicorn worker inside the API container (no `--workers`). In-memory rate limiting is **process-local**; JWT denylist and distributed limits need Redis.

| Mode                         | Guidance                                                                                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Default B0 (`make api-up`)   | Single process in the Compose image; no `--reload`                                                                                         |
| Multi-worker / multi-replica | Set `REDIS_ENABLED=true` and `REDIS_RATE_LIMIT_ENABLED=true` before `--workers N` (N>1). Denylist stays fail-closed when Redis is required |
| Compose `CMD`                | Never add `--reload` or `--workers` without an explicit ops decision                                                                       |

Defer gunicorn + uvicorn worker fleets unless a short ADR justifies them.

### Optional — hosted Postgres / pooler tips

If you use a transaction pooler (including Supabase PG), copy [`environments/staging/.env.example`](../../environments/staging/.env.example), set `PAPITA_ENV=staging`, and keep migrations on `DATABASE_URL_MIGRATIONS` (`:5432`). See [`environments/README.md`](../../environments/README.md) and the [optional pooler checklist](../../docs/ops/b1-supabase-deploy-checklist.md).

```bash
# Migrate on direct URL (never transaction pooler)
PAPITA_ENV=staging /bin/bash ./bin/alembic.sh upgrade --url "$DATABASE_URL_MIGRATIONS"

# Optional pooler connectivity smoke (not an epic gate after PPT-039 Auth reissue)
PAPITA_ENV=staging make b1-smoke
```

**Engine opts:** API `Settings` pass `pool_pre_ping=True` and `pool_size=DATABASE_POOL_SIZE` into `SQLDatabaseConnector.establish`. On pooler URLs (`:6543` / `pgbouncer=true`), `max_overflow=0`.

Pooler modes: [PPT-031-C §2.2](../../docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31). **MVP Auth** is Supabase Auth — [#49](https://github.com/Elmorralito/save-ma-money/issues/49) / [reissue note](../../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49).

### Testing (PPT-040)

**Platform rule (Auth-first):** Supabase owns **users / Auth / tokens only**. Application data lives in Docker Postgres (B0) or any app Postgres URL — **not** Supabase-hosted storage. See [PPT-039 reissue](../../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49) and epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42).

| Gate                       | How to run                                                                            | Notes                                                                                                                |
| :------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------- |
| **B0** (Docker Postgres)   | `export DATABASE_URL=…` then `poetry run pytest modules/api/tests` or `./bin/test.sh` | **Required** in CI (`quality-control.yml`). Uses `AUTH_PROVIDER=local`.                                              |
| **Supabase Auth** (manual) | Run API with `AUTH_PROVIDER=supabase` + `SUPABASE_*`, then `make auth-smoke`          | Validates JWT → `/auth/me` (+ optional accounts). Not a DB gate.                                                     |
| Legacy pooler smoke        | `make b1-smoke` / `test_supabase_b1_smoke.py`                                         | **Parked / optional ops only** if someone hosts app PG behind a pooler. Not an epic or PPT-040 acceptance criterion. |

Live-DB suites (skipped without reachable Postgres): `test_auth_tenancy.py`, `test_accounts_categories_live_db.py`, `test_transactions_movements_live_db.py`, `test_reports_live_db.py`. Coverage is collected from `modules/api/src` and `modules/model/src` (Codecov `docs/coverage.xml`).

---

## Integration guide

### Authentication

**MVP:** Supabase Auth owns identity; the API verifies access JWTs (JWKS) and maps `sub` → `papita_transactions.users` / tenant `owner`. Prefer the Supabase client SDK for session lifecycle; API register/login are optional pass-through when `SUPABASE_ANON_KEY` is set. Full contract: [`ARCHITECTURE.md` Part VI](../../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e).

`AUTH_PROVIDER=local` (HS256 + `JWT_SECRET_KEY`) is for **B0 pytest / CI only**.

**Local Supabase DX (`AUTH_AUTO_CONFIRM_EMAIL`):** when `PAPITA_ENV=local` (or the env var is explicitly `true`) and `SUPABASE_SERVICE_ROLE_KEY` is set, register prefers Admin `create_user` with `email_confirm=true` (avoids SMTP confirmation emails / 429 rate limits). Login uses `supabase_sign_in_with_optional_auto_confirm`, which Admin-confirms only when Auth shows `email_confirmed_at` null — wrong passwords do not trigger confirm. Prefer turning off **Confirm email** in the Supabase dashboard for local smoke; see `environments/local/.env.example`.

**Register** — returns **201**, no token; client must log in (or obtain a Supabase session) separately.

```bash
curl -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"johndoe","email":"user@example.local","password":"SecurePass1!"}'
```

**Login** — OAuth2 form (`python-multipart`). Field `username` accepts **email or username**.

```bash
curl -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.local&password=SecurePass1!"
```

**Protected routes:**

```bash
curl -X GET "$BASE/accounts" -H "Authorization: Bearer $ACCESS_TOKEN"
```

JWT `sub` maps to `users.id`. With `AUTH_PROVIDER=supabase`, `POST /auth/refresh` and `POST /auth/logout` call Supabase session APIs (logout may also denylist the access JWT when Redis is enabled). With `AUTH_PROVIDER=local`, refresh is **501**; logout is **501** unless Redis denylist is enabled.

### Request conventions

| Header                           | When                                      |
| :------------------------------- | :---------------------------------------- |
| `Authorization: Bearer …`        | All routes except health + register/login |
| `Content-Type: application/json` | POST/PUT bodies (except login form)       |

**Pagination:** `skip` (default 0), `limit` (default 100). Response envelope: `{ "items", "total", "skip", "limit" }`.

**Transaction lists:** default **excludes** `transfer` rows — use `/movements` or `?transaction_type=transfer`.

### v3 data shapes (integration reference)

`balance` comes from the `account_balances` materialized view, not a column on `accounts`.

**Account (response):** `account_kind`, `ledger_side`, `currency`, `balance`, optional `banking_details` / etc. by kind. **Removed:** `account_type`, `metadata`, `initial_balance` (use `initial_value` on create).

**Category:** `category_type` (API) → `category_kind` (DB). **Removed:** `budget_allocation`.

**Transaction:** `transaction_type` → `transaction_kind`; `transaction_date` → `transaction_ts`. **Removed:** `budget_id`, `attachments`, `metadata`, `recurrence_rule`.

**Movement:** alias over TRANSFER — `source_account_id` / `destination_account_id` map to `from_account_id` / `to_account_id`.

### SDK examples

**Python (httpx):**

```python
import httpx

BASE = "http://localhost:8000/api/v1"

async def register_and_login() -> str:
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE}/auth/register", json={
            "username": "johndoe",
            "email": "user@example.local",
            "password": "SecurePass1!",
        })
        login = await client.post(
            f"{BASE}/auth/login",
            data={"username": "user@example.local", "password": "SecurePass1!"},
        )
        login.raise_for_status()
        return login.json()["access_token"]
```

**cURL — transfer:**

```bash
curl -X POST "$BASE/movements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_account_id": "from-uuid",
    "destination_account_id": "to-uuid",
    "amount": 500.0,
    "currency": "USD",
    "movement_date": "2026-02-04"
  }'
```

### Error handling

| HTTP | Typical cause                                                                |
| :--- | :--------------------------------------------------------------------------- |
| 401  | Invalid/expired JWT or bad login                                             |
| 403  | Insufficient permissions                                                     |
| 404  | Not found (including other tenant's IDs)                                     |
| 409  | Duplicate username/email on register                                         |
| 422  | Pydantic / DTO validation                                                    |
| 501  | Deferred endpoint (budgets, split, budget-performance; local refresh/logout) |

Webhooks are **not implemented** (future: `transaction.created`, etc.).

---

## Endpoint reference

### Endpoint summary

| Resource       | Endpoint          | Methods                | MVP scope                 |
| -------------- | ----------------- | ---------------------- | ------------------------- |
| Health         | `/health`         | GET                    | ✓                         |
| Authentication | `/auth/*`         | POST                   | register, login only      |
| Accounts       | `/accounts/*`     | GET, POST, PUT, DELETE | ✓                         |
| Categories     | `/categories/*`   | GET, POST, PUT, DELETE | ✓                         |
| Budgets        | `/budgets/*`      | GET, POST, PUT, DELETE | **Deferred**              |
| Transactions   | `/transactions/*` | GET, POST, PUT, DELETE | ✓ (no split)              |
| Movements      | `/movements/*`    | GET, POST, PUT, DELETE | ✓ (alias)                 |
| Reports        | `/reports/*`      | GET                    | ✓ (no budget-performance) |

---

## Health Check Endpoints

### GET /health

Check API health status (includes database connectivity and probe latency).

**Response 200:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-04T15:14:00Z",
  "database": "connected",
  "database_latency_ms": 2.5
}
```

### GET /health/database

Probe API↔database communication health (`SELECT 1` + round-trip latency).

**Response 200:**

```json
{
  "status": "healthy",
  "connected": true,
  "latency_ms": 2.5,
  "checked_at": "2026-02-04T15:14:00Z",
  "detail": "api-database link healthy"
}
```

Returns **503** with `"status": "unhealthy"` and an allowlisted `detail` (never raw DB/exception text) when PostgreSQL is unreachable.

Probe SQL is a constant parameterized expression (`select(literal(1))`); health routes take no query/body input that reaches the database.

### GET /health/ready

Readiness probe for Kubernetes.

**Response 200:**

```json
{
  "ready": true
}
```

### GET /health/live

Liveness probe for Kubernetes.

**Response 200:**

```json
{
  "alive": true
}
```

---

## Authentication Endpoints

> **Auth contract:** [`ARCHITECTURE.md` Part VI](../../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e) (FR-10, FR-11, G5) · [#49](https://github.com/Elmorralito/save-ma-money/issues/49).
> **Platform:** **Supabase Auth** for access JWTs. Local HS256 = tests only. App DB = Docker / any Postgres (Supabase PG optional).

### Auth strategy summary

| Topic            | MVP behavior                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------ |
| Identity         | Supabase Auth (`AUTH_PROVIDER=supabase`); provision `users` via `ensure_from_auth_subject` |
| Register         | Prefer client → Supabase; API pass-through → **201** (no token)                            |
| Login            | Prefer client → Supabase; API OAuth2 form → access (+ refresh) token                       |
| Login identifier | Form field `username` accepts **email or username**                                        |
| JWT `sub`        | Auth subject UUID → `users.id` (local mode: `str(users.id)` from HS256 mint)               |
| Protected routes | `Authorization: Bearer` → JWKS/HS256 verify → `get_current_owner()` → tenant `owner_id`    |
| Refresh          | Supabase: rotate session. Local: **501**                                                   |
| Logout           | Supabase: Auth sign-out (+ optional Redis denylist). Local: denylist if Redis else **501** |

**Bootstrap:** FastAPI lifespan calls `UsersService.ensure_password_manager()` (still required for local + provision hashing; NFR-08).

### POST /auth/register

Register a new user. Maps to `users` table / `UsersDTO` via `UsersService.register()`.

**Business rules:**

1. Password hashed with **Argon2** on persist (`UsersDTO._serialize()`).
2. Reject duplicate username → **409** `Username already registered`.
3. Reject duplicate email → **409** `Email already registered`.
4. Invalid fields → **422** (Pydantic / `UsersDTO` validators).
5. Does **not** return a JWT — client calls `/auth/login` after register.

**Request Body:**

```json
{
  "username": "johndoe",
  "email": "user@example.local",
  "password": "SecurePass1!"
}
```

| Field      | v3 column        | Validation               |
| ---------- | ---------------- | ------------------------ |
| `username` | `users.username` | min 6 chars, unique      |
| `email`    | `users.email`    | unique, valid email      |
| `password` | `users.password` | Argon2-hashed on persist |

> **Breaking change:** `full_name` removed — use `username` for display identity.

**Response 201:**

```json
{
  "id": "uuid",
  "username": "johndoe",
  "email": "user@example.local",
  "created_at": "2026-02-04T15:14:00Z"
}
```

### POST /auth/login

Authenticate user and get access token. Requires `Content-Type: application/x-www-form-urlencoded` (`python-multipart`).

**Flow:** `OAuth2PasswordRequestForm` → `UsersService.verify_credentials()` → `AuthSecurityManager.generate_token(sub=str(user.id))`.

**Request Body (form-data):**

```
username: user@example.local
password: SecurePass1!
```

> **Login identifier:** `username` form field accepts **email or username**. Unknown user and wrong password both return **401** (no enumeration).

**Response 200:**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

> `expires_in` equals `JWT_EXPIRATION_TIME_SECONDS` from server config (default 3600).

**Response 401:**

```json
{
  "detail": "Incorrect username or password"
}
```

### POST /auth/refresh

Rotate Supabase Auth access/refresh tokens (`AUTH_PROVIDER=supabase`). Returns **501** when `AUTH_PROVIDER=local`.

**Request body:**

```json
{
  "refresh_token": "…"
}
```

**Response 200:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "…",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /auth/logout

Supabase: Auth sign-out using refresh token; optional Redis denylist for the access JWT. Local: **204** if Redis denylist is enabled, else **501**. Access token may be in the JSON body or `Authorization: Bearer`.

**Request body (Supabase):**

```json
{
  "refresh_token": "…",
  "access_token": "…"
}
```

**Response:** **204 No Content** on success.

---

## Account Endpoints

Maps to `accounts` table + optional 1:1 extension tables (`banking_account_details`, etc.) per `account_kind`.
Read `balance` from `account_balances` materialized view.

### GET /accounts

Retrieve all accounts for the authenticated user.

**Query Parameters:**

| Parameter    | Type    | Required | Description                                              |
| ------------ | ------- | -------- | -------------------------------------------------------- |
| skip         | integer | No       | Number of records to skip (default: 0)                   |
| limit        | integer | No       | Maximum records to return (default: 100)                 |
| account_kind | string  | No       | Filter by kind (`checking`, `savings`, `credit_card`, …) |
| ledger_side  | string  | No       | Filter by `asset` or `liability`                         |
| is_active    | boolean | No       | Filter by active status                                  |

> **v3 note:** `account_type` query param renamed to `account_kind` (maps to `accounts.account_kind` enum).

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Main Checking",
      "account_kind": "checking",
      "ledger_side": "asset",
      "currency": "USD",
      "balance": 5000.0,
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-02-04T15:14:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /accounts/{account_id}

Retrieve a specific account by ID.

**Path Parameters:**

| Parameter  | Type          | Required | Description        |
| ---------- | ------------- | -------- | ------------------ |
| account_id | string (UUID) | Yes      | Account identifier |

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Main Checking",
  "account_kind": "checking",
  "ledger_side": "asset",
  "currency": "USD",
  "balance": 5000.0,
  "is_active": true,
  "opened_at": "2026-01-01T00:00:00Z",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

> **v3 note:** `balance` is read from `account_balances` view. `metadata` replaced by typed extension fields per `account_kind` (e.g. `banking_account_details.entity`).

### POST /accounts

Create a new account.

**Request Body:**

```json
{
  "name": "Savings Account",
  "account_kind": "savings",
  "currency": "USD",
  "initial_value": 1000.0,
  "banking_details": {
    "entity": "Example Bank",
    "account_number": "****1234"
  }
}
```

> **v3 note:** `initial_balance` → `initial_value`. Response `balance` uses the `account_balances` materialized view when a row exists; otherwise it falls back to `initial_value` until an opening ledger transaction is posted (PPT-037). Optional opening-balance `INCOME` transaction may be created on register. For liability accounts use `account_kind: "credit_card"` or `"loan_mortgage"` with `ledger_side: "liability"`.

**Response 201:**

```json
{
  "id": "uuid",
  "name": "Savings Account",
  "account_kind": "savings",
  "ledger_side": "asset",
  "currency": "USD",
  "balance": 1000.0,
  "is_active": true,
  "banking_details": {
    "entity": "Example Bank",
    "account_number": "****1234"
  },
  "created_at": "2026-02-04T15:14:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### PUT /accounts/{account_id}

Update an existing account.

**Request Body:**

```json
{
  "name": "Updated Account Name",
  "is_active": true
}
```

> Extension fields (`banking_details`, etc.) updatable when `account_kind` matches.

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Updated Account Name",
  "account_kind": "savings",
  "ledger_side": "asset",
  "currency": "USD",
  "balance": 1000.0,
  "is_active": true,
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### DELETE /accounts/{account_id}

Soft delete an account.

**Response 204:** No Content

### GET /accounts/{account_id}/balance

Get current balance for an account (from `account_balances` materialized view).

**Response 200:**

```json
{
  "account_id": "uuid",
  "balance": 5000.0,
  "currency": "USD",
  "as_of": "2026-02-04T15:14:00Z"
}
```

---

## Category Endpoints

Maps to `categories` table. Income/expense taxonomy only — **not** v0 `types` (ASSETS/LIABILITIES classification lives on `accounts.account_kind`).

API `category_type` maps to v3 `category_kind`: `income` ↔ `INCOME`, `expense` ↔ `EXPENSE`.

### GET /categories

Retrieve all categories.

**Query Parameters:**

| Parameter     | Type    | Required | Description                     |
| ------------- | ------- | -------- | ------------------------------- |
| skip          | integer | No       | Number of records to skip       |
| limit         | integer | No       | Maximum records to return       |
| parent_id     | string  | No       | Filter by parent category       |
| category_type | string  | No       | Filter by type (income/expense) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Food & Dining",
      "category_type": "expense",
      "parent_id": null,
      "icon": "utensils",
      "color": "#FF5733",
      "is_active": true,
      "subcategories": [
        {
          "id": "uuid",
          "name": "Restaurants",
          "category_type": "expense"
        }
      ]
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /categories/{category_id}

Retrieve a specific category.

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Food & Dining",
  "category_type": "expense",
  "parent_id": null,
  "icon": "utensils",
  "color": "#FF5733",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

> **v3 note:** `budget_allocation` removed — budgets deferred (FR-09).

### POST /categories

Create a new category.

**Request Body:**

```json
{
  "name": "Entertainment",
  "category_type": "expense",
  "parent_id": null,
  "icon": "film",
  "color": "#9B59B6"
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "name": "Entertainment",
  "category_type": "expense",
  "parent_id": null,
  "icon": "film",
  "color": "#9B59B6",
  "is_active": true,
  "created_at": "2026-02-04T15:14:00Z"
}
```

### PUT /categories/{category_id}

Update a category.

**Response 200:** Updated category object

### DELETE /categories/{category_id}

Delete a category.

**Response 204:** No Content

---

## Budget Endpoints

> **MVP status: Deferred (501).** No v3 tables. Full design in [`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a) §4.1 (v4.1 migration). Endpoints retained below for post-MVP reference only.

### GET /budgets

Retrieve all budgets.

**Query Parameters:**

| Parameter  | Type    | Required | Description                       |
| ---------- | ------- | -------- | --------------------------------- |
| skip       | integer | No       | Number of records to skip         |
| limit      | integer | No       | Maximum records to return         |
| period     | string  | No       | Filter by period (monthly/yearly) |
| start_date | date    | No       | Filter by start date              |
| end_date   | date    | No       | Filter by end date                |
| status     | string  | No       | Filter by status (active/closed)  |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "February 2026 Budget",
      "period": "monthly",
      "start_date": "2026-02-01",
      "end_date": "2026-02-28",
      "total_amount": 5000.0,
      "spent_amount": 1250.0,
      "remaining_amount": 3750.0,
      "currency": "USD",
      "status": "active",
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /budgets/{budget_id}

Retrieve a specific budget with details.

**Response 200:**

```json
{
  "id": "uuid",
  "name": "February 2026 Budget",
  "period": "monthly",
  "start_date": "2026-02-01",
  "end_date": "2026-02-28",
  "total_amount": 5000.0,
  "spent_amount": 1250.0,
  "remaining_amount": 3750.0,
  "currency": "USD",
  "status": "active",
  "allocations": [
    {
      "category_id": "uuid",
      "category_name": "Food & Dining",
      "allocated_amount": 500.0,
      "spent_amount": 125.0,
      "remaining_amount": 375.0
    }
  ],
  "created_at": "2026-02-01T00:00:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### POST /budgets

Create a new budget.

**Request Body:**

```json
{
  "name": "March 2026 Budget",
  "period": "monthly",
  "start_date": "2026-03-01",
  "end_date": "2026-03-31",
  "total_amount": 5500.0,
  "currency": "USD",
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 600.0
    }
  ]
}
```

**Response 201:** Created budget object

### PUT /budgets/{budget_id}

Update a budget.

**Request Body:**

```json
{
  "name": "Updated Budget Name",
  "total_amount": 6000.0,
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 700.0
    }
  ]
}
```

**Response 200:** Updated budget object

### DELETE /budgets/{budget_id}

Delete a budget.

**Response 204:** No Content

### GET /budgets/{budget_id}/summary

Get budget summary with spending analysis.

**Response 200:**

```json
{
  "budget_id": "uuid",
  "total_budget": 5000.0,
  "total_spent": 1250.0,
  "total_remaining": 3750.0,
  "percentage_used": 25.0,
  "days_remaining": 24,
  "daily_average_spent": 312.5,
  "projected_total_spend": 4375.0,
  "status": "on_track",
  "category_breakdown": [
    {
      "category_id": "uuid",
      "category_name": "Food & Dining",
      "allocated": 500.0,
      "spent": 125.0,
      "percentage_used": 25.0
    }
  ]
}
```

### POST /budgets/{budget_id}/allocations

Add or update budget allocations.

**Request Body:**

```json
{
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 500.0
    }
  ]
}
```

**Response 200:** Updated allocations

---

## Transaction Endpoints

Maps to `transactions` table. `transaction_type` in API maps to v3 `transaction_kind` (`income`/`expense`/`transfer`).

- **INCOME / EXPENSE** — use this router; `account_id` maps to `to_account_id` (income) or `from_account_id` (expense).
- **TRANSFER** — prefer `/movements/*` alias; or filter `GET /transactions?transaction_type=transfer`.

Default `GET /transactions` **excludes** `TRANSFER` rows to avoid duplicating `/movements` listings.

### GET /transactions

Retrieve all transactions.

**Query Parameters:**

| Parameter        | Type    | Required | Description                                    |
| ---------------- | ------- | -------- | ---------------------------------------------- |
| skip             | integer | No       | Number of records to skip                      |
| limit            | integer | No       | Maximum records to return                      |
| account_id       | string  | No       | Filter by primary account (from or to)         |
| category_id      | string  | No       | Filter by category                             |
| transaction_type | string  | No       | Filter by kind (income/expense/transfer)       |
| status           | string  | No       | Filter by status (pending/completed/cancelled) |
| start_date       | date    | No       | Filter by start date                           |
| end_date         | date    | No       | Filter by end date                             |
| min_amount       | number  | No       | Minimum amount filter                          |
| max_amount       | number  | No       | Maximum amount filter                          |
| search           | string  | No       | Search in description                          |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "category_id": "uuid",
      "transaction_type": "expense",
      "status": "completed",
      "amount": 45.5,
      "currency": "USD",
      "description": "Lunch at restaurant",
      "transaction_date": "2026-02-04",
      "reference_number": "TXN-001",
      "tags": ["food", "dining"],
      "is_recurring": false,
      "template_id": null,
      "created_at": "2026-02-04T12:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /transactions/{transaction_id}

Retrieve a specific transaction.

**Response 200:**

```json
{
  "id": "uuid",
  "account_id": "uuid",
  "account_name": "Main Checking",
  "category_id": "uuid",
  "category_name": "Food & Dining",
  "transaction_type": "expense",
  "status": "completed",
  "amount": 45.5,
  "currency": "USD",
  "description": "Lunch at restaurant",
  "transaction_date": "2026-02-04",
  "reference_number": "TXN-001",
  "tags": ["food", "dining"],
  "is_recurring": false,
  "template_id": null,
  "created_at": "2026-02-04T12:30:00Z",
  "updated_at": "2026-02-04T12:30:00Z"
}
```

> **v3 note:** `budget_id`, `attachments`, `metadata`, `recurrence_rule` removed from MVP. `is_recurring` = `template_id IS NOT NULL`.

### POST /transactions

Create a new transaction.

**Request Body:**

```json
{
  "account_id": "uuid",
  "category_id": "uuid",
  "transaction_type": "expense",
  "amount": 75.0,
  "currency": "USD",
  "description": "Grocery shopping",
  "transaction_date": "2026-02-04",
  "tags": ["groceries", "food"]
}
```

> Service layer maps `account_id` + `transaction_type` to `from_account_id` / `to_account_id` / `category_id` per v3 CHECK constraints.

**Response 201:** Created transaction object

### POST /transactions/bulk

Create multiple transactions at once.

**Request Body:**

```json
{
  "transactions": [
    {
      "account_id": "uuid",
      "category_id": "uuid",
      "transaction_type": "expense",
      "amount": 50.0,
      "description": "Transaction 1",
      "transaction_date": "2026-02-04"
    },
    {
      "account_id": "uuid",
      "category_id": "uuid",
      "transaction_type": "expense",
      "amount": 30.0,
      "description": "Transaction 2",
      "transaction_date": "2026-02-04"
    }
  ]
}
```

**Response 201:**

```json
{
  "created": 2,
  "failed": 0,
  "transactions": [...]
}
```

### PUT /transactions/{transaction_id}

Update a transaction.

**Response 200:** Updated transaction object

### DELETE /transactions/{transaction_id}

Delete a transaction.

**Response 204:** No Content

### POST /transactions/{transaction_id}/split

> **MVP status: Deferred (501).** Requires v4 `transaction_splits` table ([`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a)).

Split a transaction into multiple parts.

**Request Body:**

```json
{
  "splits": [
    {
      "category_id": "uuid",
      "amount": 30.0,
      "description": "Part 1"
    },
    {
      "category_id": "uuid",
      "amount": 20.0,
      "description": "Part 2"
    }
  ]
}
```

**Response 200:** Split transaction details

---

## Movement Endpoints

**Router alias** over `transactions` where `transaction_kind = TRANSFER`. No separate `movements` table.

| API field                | v3 column         |
| ------------------------ | ----------------- |
| `source_account_id`      | `from_account_id` |
| `destination_account_id` | `to_account_id`   |
| `movement_date`          | `transaction_ts`  |
| `movement_id`            | `transactions.id` |

`scheduled: true` creates row with `status = PENDING`. `POST .../execute` sets `status = COMPLETED`.

### GET /movements

Retrieve all movements (transfers between accounts).

**Query Parameters:**

| Parameter              | Type    | Required | Description                   |
| ---------------------- | ------- | -------- | ----------------------------- |
| skip                   | integer | No       | Number of records to skip     |
| limit                  | integer | No       | Maximum records to return     |
| source_account_id      | string  | No       | Filter by source account      |
| destination_account_id | string  | No       | Filter by destination account |
| status                 | string  | No       | Filter by status              |
| start_date             | date    | No       | Filter by start date          |
| end_date               | date    | No       | Filter by end date            |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "source_account_id": "uuid",
      "source_account_name": "Checking",
      "destination_account_id": "uuid",
      "destination_account_name": "Savings",
      "amount": 500.0,
      "currency": "USD",
      "status": "completed",
      "description": "Monthly savings transfer",
      "movement_date": "2026-02-01",
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /movements/{movement_id}

Retrieve a specific movement.

**Response 200:** Movement object with full details

### POST /movements

Create a new movement (transfer).

**Request Body:**

```json
{
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "amount": 1000.0,
  "currency": "USD",
  "description": "Transfer to savings",
  "movement_date": "2026-02-04",
  "scheduled": false
}
```

> **v3 validation:** `currency` must match `accounts.currency` on both source and destination accounts. Cross-currency transfers are rejected (422).

**Response 201:** Created movement object (includes `currency`, `status`: `completed` or `pending` if `scheduled: true`)

### PUT /movements/{movement_id}

Update a pending movement.

**Response 200:** Updated movement object

### DELETE /movements/{movement_id}

Cancel a pending movement.

**Response 204:** No Content

### POST /movements/{movement_id}/execute

Execute a scheduled movement.

**Response 200:**

```json
{
  "id": "uuid",
  "status": "completed",
  "executed_at": "2026-02-04T15:14:00Z"
}
```

---

## Report Endpoints

Read-only aggregations over `transactions`, `categories`, `accounts`, and `account_balances` view. No report tables in v3.

### GET /reports/spending

Get spending report. Aggregates **posted expense activity only**.

**Query rules (v3):**

- Include rows where `transaction_kind = EXPENSE` and `status = completed` only (excludes pending/cancelled and all TRANSFER rows).
- Income totals in the response come from separate `transaction_kind = INCOME` aggregation (also `status = completed`).
- Refresh `account_balances` materialized view before date-boundary queries if balances are referenced.

**Query Parameters:**

| Parameter  | Type   | Required | Description                                |
| ---------- | ------ | -------- | ------------------------------------------ |
| start_date | date   | Yes      | Report start date                          |
| end_date   | date   | Yes      | Report end date                            |
| group_by   | string | No       | Group by (category/account/day/week/month) |
| account_id | string | No       | Filter by account                          |

**Response 200:**

```json
{
  "period": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  },
  "total_spending": 2500.0,
  "total_income": 5000.0,
  "net_savings": 2500.0,
  "breakdown": [
    {
      "category": "Food & Dining",
      "amount": 450.0,
      "percentage": 18.0,
      "transaction_count": 15
    }
  ],
  "trend": [
    {
      "date": "2026-02-01",
      "spending": 100.0,
      "income": 0.0
    }
  ]
}
```

### GET /reports/budget-performance

> **MVP status: Deferred (501).** Requires v4 `budgets` tables (FR-09, FR-12).

Get budget performance report.

**Query Parameters:**

| Parameter | Type   | Required | Description                       |
| --------- | ------ | -------- | --------------------------------- |
| budget_id | string | No       | Specific budget ID                |
| period    | string | No       | Period (monthly/quarterly/yearly) |

**Response 200:**

```json
{
  "budgets": [
    {
      "budget_id": "uuid",
      "budget_name": "February 2026",
      "total_budget": 5000.0,
      "total_spent": 2500.0,
      "variance": 2500.0,
      "performance_score": 85,
      "categories": [
        {
          "category_name": "Food & Dining",
          "budgeted": 500.0,
          "actual": 450.0,
          "variance": 50.0,
          "status": "under_budget"
        }
      ]
    }
  ]
}
```

### GET /reports/cash-flow

Get cash flow report. Portfolio-level inflows/outflows derived from per-account ledger activity.

**Query rules (v3):**

- Include only `status = completed` transactions in inflow/outflow sums.
- Inflows: `INCOME` rows (`to_account_id` set) plus inbound legs of `TRANSFER` (`to_account_id`).
- Outflows: `EXPENSE` rows (`from_account_id` set) plus outbound legs of `TRANSFER` (`from_account_id`).
- `opening_balance` / `closing_balance` are sums of `account_balances.balance` across tenant accounts at period start/end (not a stored portfolio column).
- `by_account` breaks down net activity per account for the period.

**Response 200:**

```json
{
  "period": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  },
  "opening_balance": 10000.0,
  "closing_balance": 12500.0,
  "total_inflows": 5000.0,
  "total_outflows": 2500.0,
  "net_cash_flow": 2500.0,
  "by_account": [
    {
      "account_id": "uuid",
      "account_name": "Checking",
      "inflows": 5000.0,
      "outflows": 2000.0,
      "net": 3000.0
    }
  ]
}
```

### GET /reports/trends

Get spending trends analysis.

**Query Parameters:**

| Parameter   | Type    | Required | Description                              |
| ----------- | ------- | -------- | ---------------------------------------- |
| months      | integer | No       | Number of months to analyze (default: 6) |
| category_id | string  | No       | Filter by category                       |

**Response 200:**

```json
{
  "analysis_period": {
    "start": "2025-09-01",
    "end": "2026-02-28"
  },
  "monthly_trends": [
    {
      "month": "2026-02",
      "total_spending": 2500.0,
      "total_income": 5000.0,
      "savings_rate": 50.0
    }
  ],
  "category_trends": [
    {
      "category": "Food & Dining",
      "average_monthly": 450.0,
      "trend": "stable",
      "change_percentage": 2.5
    }
  ],
  "insights": [
    {
      "type": "warning",
      "message": "Entertainment spending increased 25% this month"
    }
  ]
}
```

### GET /reports/export

Export report data.

**Query Parameters:**

| Parameter   | Type   | Required | Description                  |
| ----------- | ------ | -------- | ---------------------------- |
| report_type | string | Yes      | Type of report               |
| format      | string | Yes      | Export format (csv/xlsx/pdf) |
| start_date  | date   | Yes      | Start date                   |
| end_date    | date   | Yes      | End date                     |

**Response 200:** File download

---

## MVP delivery order ([#42](https://github.com/Elmorralito/save-ma-money/issues/42))

All rows below are **shipped** (child issues closed). Mapping: [`ARCHITECTURE.md` Part IV](../../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) §6.

| Priority | Endpoints                                                                                | Issue                                                                                                                        |
| -------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| P1       | `GET /health`, `/health/database`, `/health/ready`, `/health/live` (+ `/auth`, `/redis`) | [#45](https://github.com/Elmorralito/save-ma-money/issues/45)                                                                |
| P2       | `POST /auth/register`, `POST /auth/login`, `/me`, OAuth/SSO; Supabase refresh/logout     | [#44](https://github.com/Elmorralito/save-ma-money/issues/44), [#49](https://github.com/Elmorralito/save-ma-money/issues/49) |
| P3       | `/accounts/*` CRUD + balance                                                             | [#46](https://github.com/Elmorralito/save-ma-money/issues/46)                                                                |
| P4       | `/categories/*`, `/transactions/*`, `/movements/*`                                       | [#46](https://github.com/Elmorralito/save-ma-money/issues/46), [#47](https://github.com/Elmorralito/save-ma-money/issues/47) |
| P5       | `/reports/spending`, `/reports/cash-flow`, `/reports/trends`, `/reports/export`          | [#48](https://github.com/Elmorralito/save-ma-money/issues/48)                                                                |

**Still 501:** all `/budgets/*`, `POST /transactions/{id}/split`, `GET /reports/budget-performance`. Refresh/logout **501 only** when `AUTH_PROVIDER=local` (without Redis denylist for logout).

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "amount",
      "message": "Amount must be positive"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

### 409 Conflict

Registration conflicts (duplicate username or email):

```json
{
  "detail": "Username already registered"
}
```

```json
{
  "detail": "Email already registered"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found",
  "resource_type": "Transaction",
  "resource_id": "uuid"
}
```

### 501 Not Implemented

Returned for deferred endpoints (budgets, transaction split, budget-performance report) and for auth refresh/logout when `AUTH_PROVIDER=local` (see Auth section).

```json
{
  "detail": "Not implemented in MVP — see ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33",
  "deferred_reason": "FR-09 budgets deferred to v4.1"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "amount"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

---

## Rate Limiting

**Auth** (`/auth/login`, `/auth/register`, OAuth) uses a **per-IP** sliding window
(`AUTH_*_RATE_LIMIT_*`). **Protected CRUD/report routes** use **tenant-scoped**
Free / Pro / Enterprise quotas (`API_RATE_LIMIT_*`) keyed by `owner_id` (minute + day
windows). Counters are in-memory by default; with `REDIS_ENABLED=true` and
`REDIS_RATE_LIMIT_ENABLED=true` they are shared across replicas via Redis.

| Tier       | Requests/Minute | Requests/Day |
| ---------- | --------------- | ------------ |
| Free       | 60              | 1,000        |
| Pro        | 300             | 10,000       |
| Enterprise | Unlimited       | Unlimited    |

Default tier is `API_RATE_LIMIT_DEFAULT_TIER` (usually `free`). Optional Redis override:
`papita:{env}:{owner_id}:api_tier` → `free` \| `pro` \| `enterprise`. Disable tenant
quotas with `API_RATE_LIMIT_ENABLED=false`.

Rate limit headers (success and 429):

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1707058440
X-RateLimit-Tier: free
Retry-After: 12   # on 429 only
```

---

## Redis (PPT-043)

Optional shared infrastructure for cache-aside, distributed rate limits, and
(session denylist / broker scaffolds). PostgreSQL remains the source of truth.

```
[ Client ] → [ API Server ] → [ Redis ]     (hit: fast return)
                    ↓ miss
            [ PostgreSQL B0/B1 ]
```

| Variable                               | Default                                     | Purpose                                           |
| -------------------------------------- | ------------------------------------------- | ------------------------------------------------- |
| `REDIS_URL`                            | unset                                       | Redis connection URL (`redis://…` / `rediss://…`) |
| `REDIS_ENABLED`                        | `false` (unit tests) / `true` (Compose API) | Init pool + include Redis in `/health/ready`      |
| `REDIS_DEFAULT_TTL_SECONDS`            | `60`                                        | Legacy; unused — prefer per-namespace TTLs below  |
| `REDIS_CACHE_TTL_ACCOUNTS_SECONDS`     | `60`                                        | `GET /accounts` list TTL                          |
| `REDIS_CACHE_TTL_CATEGORIES_SECONDS`   | `300`                                       | `GET /categories` list TTL                        |
| `REDIS_CACHE_TTL_REPORTS_SECONDS`      | `180`                                       | Reports TTL (tune 120–300s)                       |
| `REDIS_CACHE_TTL_TRANSACTIONS_SECONDS` | `15`                                        | Short TTL for `GET /transactions` list/detail     |
| `REDIS_IDEMPOTENCY_TTL_SECONDS`        | `86400`                                     | Replay window for `Idempotency-Key` on creates    |
| `REDIS_RATE_LIMIT_ENABLED`             | `false` (unit tests) / `true` (Compose API) | Use Redis for auth/API rate-limit counters        |
| `REDIS_MAX_CONNECTIONS`                | `10`                                        | Connection pool size                              |

B0 deploy: `make api-up` (or `make stack-up`). Compose API always uses
`redis://redis:6379/0` (hardcoded — do not inject host `localhost`). Smoke:
`make redis-smoke`. Checklist:
[`docs/ops/redis-deploy-checklist.md`](../../docs/ops/redis-deploy-checklist.md).

When `REDIS_ENABLED=false`, the API keeps in-memory rate limiting and skips
caching/denylist; unit tests remain green without Redis.

**Key prefix:** all Redis keys are `papita:{PAPITA_ENV}:…` so local/staging/production
do not collide on shared Redis.

**Fail policy:** cache and rate limits **fail open** (miss / allow) on Redis errors.
JWT denylist **fails closed** when Redis is required (`REDIS_ENABLED=true`): Redis
errors → HTTP 503 on protected routes so a blip cannot resurrect a revoked token.

**Client model:** sync `redis` via lifespan; fine while most handlers are sync
(threadpool). Prefer `redis.asyncio` when more routes are async-heavy.

Protected cache keys are tenant-scoped, env-prefixed, and **versioned**:
`papita:{env}:{owner_id}:{route}:v{version}:{hash(params)}`. Mutations bump a
per-tenant namespace counter so prior entries miss without SCAN. Successful GETs
may return `X-Cache: HIT|MISS|BYPASS`.

| Mutation                      | Invalidates                                      |
| ----------------------------- | ------------------------------------------------ |
| Account create/update/delete  | `accounts`, `reports`                            |
| Category create/update/delete | `categories`, `reports`                          |
| Transaction / movement writes | `transactions`, `reports`, `accounts` (balances) |

`POST /transactions` and `POST /transactions/bulk` accept optional
`Idempotency-Key` (when Redis is enabled) so safe retries replay the original
201 body without double-inserting.

Logout denylists access tokens in Redis (local + Supabase); protected routes
reject revoked JWTs until TTL expires.

---

## Related documentation

| Document                                                                                                                                                             | Purpose                                                                                   |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- |
| This file                                                                                                                                                            | **Canonical** API reference (status, setup, integration, endpoint catalog)                |
| [`environments/README.md`](../../environments/README.md)                                                                                                             | `PAPITA_ENV`, Auth/DB/Redis env layout                                                    |
| [`modules/model/README.md`](../model/README.md)                                                                                                                      | v3 schema, services, handlers, testing                                                    |
| [`docs/design/README.md`](../../docs/design/README.md)                                                                                                               | PPT-031 design program index                                                              |
| [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33)                 | Endpoint → Service → DTO → SQLModel                                                       |
| [`docs/design/ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43`](../../docs/design/ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43)                     | PPT-033 validation matrix ([#43](https://github.com/Elmorralito/save-ma-money/issues/43)) |
| [`docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)                     | Supabase Auth contract (G5) — SSO, smoke, JWT/tenant rules                                |
| [`docs/issues/README.md` Part IV](../../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49)                                                             | Auth-only pivot ([#49](https://github.com/Elmorralito/save-ma-money/issues/49))           |
| [`docs/issues/README.md` Part II](../../docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31)                                                      | B0/B1/B2/B3 + G7 supersede                                                                |
| [`docs/ops/b1-supabase-deploy-checklist.md`](../../docs/ops/b1-supabase-deploy-checklist.md)                                                                         | Optional hosted PG / pooler                                                               |
| [`docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../../docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32)           | v3 DDL and constraints                                                                    |
| [`docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a) | Budgets, splits (post-MVP)                                                                |
| [`.cursor/AGENTS.md`](../../.cursor/AGENTS.md)                                                                                                                       | Agent ops: routers, test commands, PR checklist                                           |
| [`../../README.md`](../../README.md)                                                                                                                                 | Monorepo quick start                                                                      |
| [`../../CHANGELOG.md`](../../CHANGELOG.md)                                                                                                                           | Issue tracker                                                                             |
| Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42)                                                                                                   | PPT-032 program tracker                                                                   |
