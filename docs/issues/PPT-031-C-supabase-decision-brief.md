# PPT-031-C: Supabase × FastAPI integration decision record

**GitHub issue:** [#31](https://github.com/Elmorralito/save-ma-money/issues/31) · **Parent:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) · **Track:** B
**Status:** Complete (2026-07-06) · **Gate G7:** **Superseded in part (2026-07-13)** — see [G7 supersede](#g7-supersede-2026-07-13--auth-first) · Original: **Proposed — B0 (local) + B1 (stg/prod Postgres); B2/B3 deferred** (awaiting sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28))

## G7 supersede (2026-07-13) — Auth-first

**Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) pivot:** MVP Supabase usage is **Auth only** (former **B2**). **Supabase-hosted Postgres (B1 pooler) is no longer an epic acceptance requirement.** Database remains Docker Postgres locally (B0) or **any** Postgres URL in staging/prod.

| Prior G7 (this brief)                             | Current epic direction                                                                        |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| B1 = required staging/prod DB via Supabase pooler | B1 DB = **optional** ops (pooler wiring may remain in tree)                                   |
| B2 = Supabase Auth deferred                       | B2 Auth = **MVP** via PPT-039 ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)) |
| Auth = local JWT on B0/B1                         | Auth = Supabase JWT verification; local HS256 issuance deprecated                             |

Canonical reissue write-up: [`PPT-039-supabase-auth-reissue.md`](./PPT-039-supabase-auth-reissue.md). §2 pooler formats remain valid **if** operators choose Supabase as a Postgres host — they are not required for PPT-032 close-out.

---

## Document ↔ issue cross-reference

| Related document                                                                                                                                 | Issue                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| [`PPT-031-simplify-requirements.md`](./PPT-031-simplify-requirements.md)                                                                         | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — requirements (Track B) |
| [`../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)     | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) — v0 schema baseline     |
| [`../design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32) | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) — v3 tenancy (proposed)  |
| `../design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34` _(planned)_                                                                 | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) — RLS migrations (B3)    |
| `../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` _(planned)_                                                                   | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E — FR-10/11       |

## Executive decision

**Propose G7 as a phased B0 + B1 path:** use **Docker Postgres locally** (B0) for offline development, Alembic iteration, and CI parity; use **Supabase PostgreSQL** (B1) for staging and production via the pooler `DATABASE_URL`. Keep **local JWT + `papita_transactions.users`** (PR #27 investment) until `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` (G5) is written. **Defer B2 (Supabase Auth)** and **B3 (RLS; optional B2)** to a post-MVP phase — RLS policy outline is documented here for [#34](https://github.com/Elmorralito/save-ma-money/issues/34) but not implemented.

**Rationale:** B0/B1 share one Postgres dialect and require no auth rewrite mid-refactor. **DuckDB is not part of this path** — Postgres is the only supported engine going forward. v3 schema (proposed in [#32](https://github.com/Elmorralito/save-ma-money/issues/32)) already adopts app-layer tenancy (denormalized `owner_id`); RLS is optional defense-in-depth, not a G1 blocker.

---

## Platform decision (2026-07-02)

**DuckDB is deprecated and will not be used.** As of PPT-031 ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)), DuckDB is **no longer a supported database** for development, testing, CI, staging, or production. Do not use DuckDB connection strings, file storage (e.g. `.data/store.duckdb`), or DuckDB-specific code paths for new work.

| Status         | Detail                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Supported**  | **PostgreSQL only** — Docker Postgres locally (B0); Supabase for hosted/staging/production (B1)                                                                                |
| **Deprecated** | DuckDB file/in-memory backends, `DuckDBUpserter` (runtime rejection via `UpserterFactory`), `deploy/setup_duckdb.py`, and connector fallbacks that default to `duckdb://`      |
| **Superseded** | [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) — Postgres FK validation lives in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |

Legacy DuckDB code may remain in the repo until a cleanup PR removes it; that removal is **out of scope** for this decision record. **All new configuration must use `postgresql+psycopg2://` URLs** (see §2). Legacy tooling still referencing DuckDB (not authoritative): `deploy/alembic.sh` (`--duckdb-path`), `modules/model/alembic/env.py` (`AlembicDuckDBImpl`), and `SQLDatabaseConnector` fallback when `DATABASE_URL` is unset (see §4.1).

~~Former option: Self-hosted Postgres + DuckDB~~ — **removed permanently**. Do not document, evaluate, or recommend DuckDB paths.

---

## Goal

Document Supabase × FastAPI integration and produce a decision record for auth/RLS options — **not full implementation** until v3 schema is frozen ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)).

---

## 1. Options matrix and decision

### 1.1 Summary table

| Option                              | Description                                          | When to choose                                                    | **G7 decision**      |
| ----------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------- | -------------------- |
| **B0 — Local Postgres**             | Docker Postgres locally; Supabase for staging/prod   | Default for dev teams wanting offline local DB                    | **Adopt (dev)**      |
| **B1 — Supabase Postgres (remote)** | Staging/prod use Supabase pooler `DATABASE_URL`      | Hosted DB without local Docker; solo devs may use B1 for all envs | **Adopt (stg/prod)** |
| **B2 — Supabase Auth**              | OAuth/magic links via Supabase; app schema unchanged | When delegating auth to Supabase                                  | **Defer**            |
| **B3 — RLS on `owner_id`**          | Postgres RLS policies; optional B2 (Supabase Auth)   | Strongest tenant isolation at DB layer                            | **Defer**            |

### 1.2 B0 — Local Postgres (development)

|                 |                                                                                                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | `docker/database/docker-compose.yml` runs Postgres 15; `DATABASE_URL` points at `localhost`. Staging/prod use Supabase (B1).                                          |
| **Pros**        | Offline dev; fast Alembic iteration; matches CI [`migration-check.yml`](../../.github/workflows/migration-check.yml); no cloud dependency for unit/integration tests. |
| **Cons**        | Developers must run Docker; schema drift if local and remote migrations diverge; two connection configs to maintain.                                                  |
| **Code impact** | `Settings.DATABASE_URL` → `SQLDatabaseConnector.establish()` only; no Supabase SDK required.                                                                          |

### 1.3 B1 — Supabase Postgres (staging / production)

|                 |                                                                                                                                                |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | All remote environments use Supabase project connection string (pooler). Optional: solo developers may use B1 for dev too if they skip Docker. |
| **Pros**        | Single ops model; managed backups, dashboard, branching; aligns with NFR-07 FK validation on real Supabase.                                    |
| **Cons**        | Requires network; pooler mode constraints (see §2); secrets in Supabase dashboard / deployment env.                                            |
| **Code impact** | Same `DATABASE_URL` wiring as B0; document pooler URL format and engine options.                                                               |

### 1.4 B2 — Supabase Auth (deferred)

|                 |                                                                                                                                                                            |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | Replace or bridge local JWT issuance with Supabase Auth (`auth.users`); FastAPI validates Supabase JWT or exchanges session.                                               |
| **Pros**        | OAuth, magic links, MFA, hosted session management; less custom auth code long-term.                                                                                       |
| **Cons**        | Rewrites FR-10/FR-11 mid-refactor; requires `auth.users.id` ↔ `papita_transactions.users.id` sync; PR #27 `Users` + `AuthSecurityManager` investment abandoned or bridged. |
| **Defer until** | `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` (G5) explicitly evaluates Supabase Auth vs local JWT.                                                             |

### 1.5 B3 — RLS on `owner_id` (deferred)

|                 |                                                                                                                                                                                                                                                            |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | PostgreSQL RLS policies on tenant-scoped tables; API sets `app.user_id` per request from JWT `sub` (works with **B0/B1 local JWT** — Supabase Auth/B2 not required).                                                                                       |
| **Pros**        | Defense-in-depth; DB blocks cross-tenant reads even if repository filter is omitted.                                                                                                                                                                       |
| **Cons**        | Doubles isolation logic (app layer + DB); global `categories` seeds (`owner_id NULL`) need special policies; service-role bypass for admin/migrations; test matrix doubles.                                                                                |
| **Defer until** | App-layer tenancy proven (v3 + G5); implement in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) / v4.7 per [`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3). |

**Note:** B3 is **not blocked on B2**. If B2 (Supabase Auth) is adopted later, map its `sub` to `app.user_id` the same way as local JWT.

### 1.6 Phased rollout (proposed for G7)

| Phase       | Environment         | Option         | Auth                                                                                                                |
| ----------- | ------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Now**     | Local dev, CI       | B0             | Local JWT (after G5 auth contract)                                                                                  |
| **Now**     | Staging, production | B1             | Local JWT                                                                                                           |
| **Post-G5** | Any                 | Re-evaluate B2 | Supabase Auth if chosen in auth contract                                                                            |
| **Post-v3** | Staging first       | B3             | RLS on `owner_id` tables ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)); compatible with B0/B1 JWT |

---

## 2. `DATABASE_URL` formats

SQLAlchemy driver in this repo: **`postgresql+psycopg2`** (see root README and Alembic config). `Settings` passes the URL string to `SQLDatabaseConnector.establish()`, which calls `sqlalchemy.create_engine()`.

### 2.1 B0 — Local Docker Postgres

```bash
# modules/api/src/.env (API Settings) or exported for Alembic
DATABASE_URL="postgresql+psycopg2://papita:changeme@localhost:5432/papita_transactions"
```

Compose defaults: see `docker/database/docker-compose.yml`. Create `docker/database/.env` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` (or `DB_*` aliases).

**Alembic / migrations:** use a **direct** Postgres URL (not pooler). Local Docker satisfies this.

### 2.2 B1 — Supabase pooler

Supabase exposes two pooler modes ([Supabase connection docs](https://supabase.com/docs/guides/database/connecting-to-postgres)):

| Mode            | Port   | Host pattern                                                           | Use with FastAPI / SQLAlchemy                                          |
| --------------- | ------ | ---------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Transaction** | `6543` | `aws-0-<region>.pooler.supabase.com`                                   | **Default for API** — short-lived connections, serverless-friendly     |
| **Session**     | `5432` | `aws-0-<region>.pooler.supabase.com` or `db.<project-ref>.supabase.co` | Long transactions, prepared statements, `LISTEN`/`NOTIFY`, temp tables |

**Transaction mode (recommended for FastAPI request handlers):**

```bash
DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?pgbouncer=true"
```

**Session mode (direct or session pooler — use for Alembic upgrades, long-running batch jobs):**

```bash
# Pooler session mode
DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres"

# Direct connection (migrations, one-off admin)
DATABASE_URL="postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres"
```

### 2.3 SQLAlchemy engine guidance

| Concern             | Transaction pooler (6543)                                                                                                                                   | Session / direct (5432)                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Connection pooling  | Modest `pool_size=DATABASE_POOL_SIZE` (default 5) + `max_overflow=0` on pooler URLs (PPT-039 [#49](https://github.com/Elmorralito/save-ma-money/issues/49)) | Standard SQLAlchemy pool                       |
| Prepared statements | **psycopg2** (current driver): modest QueuePool is the default; switch to `NullPool` if PgBouncer timeouts appear; `prepare_threshold` is **psycopg3 only** | Default OK                                     |
| Health checks       | `pool_pre_ping=True` on API engine (wired in Settings → `establish`, PPT-039)                                                                               | Same                                           |
| Migrations          | **Avoid** transaction pooler — use direct URL or session mode                                                                                               | **Required** for `./deploy/alembic.sh upgrade` |
| SSL                 | Supabase requires TLS in production                                                                                                                         | Add `?sslmode=require` if not implicit         |

**Implementation note (PPT-039):** API `Settings` passes `pool_pre_ping=True`, `pool_size=DATABASE_POOL_SIZE`, and (on transaction-pooler URLs) `max_overflow=0` into `SQLDatabaseConnector.establish()`. Use `DATABASE_URL_MIGRATIONS` for Alembic-only direct connections while the API uses the transaction pooler. Checklist: [`docs/ops/b1-supabase-deploy-checklist.md`](../ops/b1-supabase-deploy-checklist.md).

---

## 3. Environment variables (NFR-05)

Template: [`environments/<name>/.env.example`](../../environments/README.md) — **copy to `environments/<name>/.env`** and set `PAPITA_ENV`. **Never commit real `.env` files.**

`papita_txnsapi.Settings` loads from `environments/$PAPITA_ENV/.env`. Alembic / Docker use the same file via `deploy/alembic.sh --env` and `docker compose --env-file`.

### 3.1 Variable reference

| Variable                      | Required | B0  | B1  | B2       | B3  | Purpose                                                                                               |
| ----------------------------- | -------- | --- | --- | -------- | --- | ----------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                | Yes      | ✓   | ✓   | ✓        | ✓   | SQLAlchemy URL for API runtime                                                                        |
| `JWT_SECRET_KEY`              | Yes\*    | ✓   | ✓   | —        | —   | HS256 signing for local JWT (`AuthSecurityManager`)                                                   |
| `JWT_ALGORITHM`               | No       | ✓   | ✓   | —        | —   | Default `HS256`                                                                                       |
| `JWT_EXPIRATION_TIME_SECONDS` | No       | ✓   | ✓   | —        | —   | Access token TTL (default 3600)                                                                       |
| `SUPABASE_URL`                | No       | —   | —   | ✓        | ✓   | Project URL `https://<ref>.supabase.co`                                                               |
| `SUPABASE_ANON_KEY`           | No       | —   | —   | ✓        | ✓   | Public key for client-side Supabase Auth                                                              |
| `SUPABASE_SERVICE_ROLE_KEY`   | No       | —   | —   | Optional | ✓   | Server-side admin / bypass RLS (**never expose to client**)                                           |
| `ALLOWED_ORIGINS`             | No       | ✓   | ✓   | ✓        | ✓   | CORS origins — JSON array in `.env` (e.g. `["http://localhost:3000"]`); pydantic-settings `list[str]` |
| `DATABASE_POOL_SIZE`          | No       | ✓   | ✓   | ✓        | ✓   | SQLAlchemy pool size (default 5); wired in API Settings (PPT-039)                                     |
| `LOG_LEVEL`                   | No       | ✓   | ✓   | ✓        | ✓   | API/model logging                                                                                     |
| `HOST` / `PORT`               | No       | ✓   | ✓   | ✓        | ✓   | Uvicorn bind (default `0.0.0.0:8000`)                                                                 |

\* `JWT_SECRET_KEY` required for B0/B1 local JWT path. If B2 is adopted later, API may validate Supabase JWTs with Supabase JWKS instead; document swap in auth contract.

### 3.2 Per-environment examples

| Environment     | `DATABASE_URL` source                | Other vars                                           |
| --------------- | ------------------------------------ | ---------------------------------------------------- |
| Local dev (B0)  | `localhost:5432` via Docker          | `JWT_SECRET_KEY` (dev-only secret)                   |
| CI              | Ephemeral Postgres service container | Test `JWT_SECRET_KEY` from workflow env              |
| Staging (B1)    | Supabase transaction pooler `:6543`  | Production-grade `JWT_SECRET_KEY` in secrets manager |
| Production (B1) | Supabase transaction pooler `:6543`  | Same; rotate keys via deployment platform            |

---

## 4. FastAPI integration notes

FastAPI app (`main.py`, routers) is **not implemented yet** ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)). This section records the intended wiring against current code.

### 4.1 Settings bootstrap

`Settings` (`modules/api/src/papita_txnsapi/config/settings.py`):

- Loads `.env` from `modules/api/src/.env`
- Validates `DATABASE_URL` via `SQLDatabaseConnector.establish(connection=value)` — engine is created at settings init
- Requires `JWT_SECRET_KEY` (no default — app fails fast without it)
- **DuckDB fallback:** if `DATABASE_URL` is missing or empty, Settings warns and calls `establish(connection=None)`, which still resolves to a legacy DuckDB path in `connector.py`. **Always set an explicit Postgres `DATABASE_URL`** in every environment until #25 removes the fallback.

### 4.2 Session dependency (recommended pattern for #25)

Repositories and services today use `@SQLDatabaseConnector.connect`, which injects `_db_session`. For FastAPI routes, expose a generator dependency:

```python
from collections.abc import Generator

from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction


def get_db_session() -> Generator[Session, None, None]:
    SQLDatabaseConnector.connected(on_disconnected=FallbackAction.RAISE)
    with Session(SQLDatabaseConnector.engine) as session:
        yield session
```

**Alternative:** call services/repositories that already use `@SQLDatabaseConnector.connect` without route-level session — both patterns are valid; pick one per layer in #25 to avoid double sessions.

**Tenant scoping:** decode JWT → `sub` as `uuid.UUID` → pass `owner_id` into `OwnedTableRepository` / service `owner=` kwargs. Aligns with v3 proposed `owner_id` on hot tables ([#32](https://github.com/Elmorralito/save-ma-money/issues/32) §3.2).

### 4.3 Auth wiring (B0/B1)

`AuthSecurityManager` (`modules/api/src/papita_txnsapi/core/security.py`):

- `generate_token(user_id)` — embeds `sub`, `exp`, `iat`, `type`
- `authenticate_and_get_token(username, password, verify_credentials)` — expects injectable verifier
- `decode_token(token)` — validates signature and expiry

**Gaps (Track E, not this issue):**

- `UsersService` has **no** `verify_credentials()` — must be added before `/auth/login`
- `PasswordManagerFactory` is **uninitialized** until `get_password_manager(keyword="argon2")` (or similar) runs at app startup

**JWT `sub` claim:** string form of `papita_transactions.users.id` (UUID). Today `UsersDTO` **deterministically** sets `id = uuid5(NAMESPACE_URL, sha256(username))` — auth contract (G5) must confirm or change this before login ships.

### 4.4 Health checks

API spec (`modules/api/API_Endpoints.md.md`) defines:

| Endpoint            | Purpose             | Implementation sketch                                                 |
| ------------------- | ------------------- | --------------------------------------------------------------------- |
| `GET /health`       | Overall status + DB | `SQLDatabaseConnector.connected()` + `session.exec(text("SELECT 1"))` |
| `GET /health/ready` | K8s readiness       | DB reachable                                                          |
| `GET /health/live`  | K8s liveness        | Process up (no DB required)                                           |

Return `"database": "connected"` only when `SELECT 1` succeeds. On Supabase B1, transient pooler errors should map to 503 on `/health/ready`, not 500 on liveness.

### 4.5 CORS

`Settings.ALLOWED_ORIGINS` defaults to `["*"]` — acceptable for local dev only.

| Environment     | Recommendation                                                                |
| --------------- | ----------------------------------------------------------------------------- |
| B0 local        | `["http://localhost:3000", "http://127.0.0.1:3000"]` or `*` for quick testing |
| B1 staging/prod | Explicit frontend origin(s); **never** `*` if `allow_credentials=True`        |
| B2/B3 (future)  | Include Supabase Auth redirect URLs if using browser OAuth                    |

Planned middleware (from API README scaffold): `CORSMiddleware` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

---

## 5. Auth implications matrix (FR-10, FR-11)

Input: Track E in [`PPT-031-simplify-requirements.md`](./PPT-031-simplify-requirements.md) §Track E, PR #27 `Users` table.

| Topic                        | B0                                                                | B1           | B2 (deferred)                                                 | B3 (deferred)                           |
| ---------------------------- | ----------------------------------------------------------------- | ------------ | ------------------------------------------------------------- | --------------------------------------- |
| **Identity store**           | `papita_transactions.users`                                       | Same         | `auth.users` + app `users` row                                | Same as B2                              |
| **Registration**             | `POST /auth/register` → `UsersService.create()`                   | Same         | Supabase `signUp` + sync row in `users`                       | Same                                    |
| **Login**                    | `POST /auth/login` → `verify_credentials` → local JWT             | Same         | Supabase session / JWT; API validates via JWKS                | Same                                    |
| **`JWT sub` claim**          | `users.id` (UUID string)                                          | Same         | Supabase `sub` OR mapped `users.id` — **must document in G5** | Same + `app.user_id` for RLS            |
| **Password hashing**         | Argon2 via `PasswordManagerFactory` bootstrap                     | Same         | Supabase handles passwords                                    | Same                                    |
| **`verify_credentials`**     | **Required** — not implemented                                    | Same         | Replaced by Supabase verify                                   | Replaced                                |
| **Refresh / logout (FR-11)** | Stateless JWT only, or refresh token + denylist — **G5 decision** | Same         | Supabase refresh tokens / revoke                              | Same                                    |
| **`AuthSecurityManager`**    | Primary token issuer                                              | Same         | Validator only or hybrid bridge                               | Validator + set `app.user_id`           |
| **Supabase env vars**        | Not required                                                      | Not required | `SUPABASE_URL`, `SUPABASE_ANON_KEY`                           | + `SUPABASE_SERVICE_ROLE_KEY` for admin |
| **Tenant isolation**         | App-layer `owner_id` filters                                      | Same         | Same                                                          | + RLS policies (§6); **no B2 required** |

**Cross-cutting prerequisites (all B-options before #25 MVP):**

1. `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` (G5) — register/login schema, refresh strategy, id mapping
2. `UsersService.verify_credentials(username, password) -> str | None`
3. `PasswordManagerFactory` initialized in FastAPI lifespan
4. `python-multipart` for OAuth2 form login (per requirements doc)

---

## 6. RLS policy outline (B3 — implementation in #34)

RLS is **deferred** (G7). v3 schema (proposed) uses **Strategy B** — denormalized `owner_id` on hot tables with app-layer enforcement ([#32](https://github.com/Elmorralito/save-ma-money/issues/32) §3.2). B3 adds **Strategy C** as defense-in-depth and works with **local JWT (B0/B1)** or Supabase Auth (B2).

### 6.1 v3 tables — RLS candidates

| Table                                       | `owner_id` | Policy notes                                                      |
| ------------------------------------------- | ---------- | ----------------------------------------------------------------- |
| `papita_transactions.accounts`              | NOT NULL   | Standard tenant isolation                                         |
| `papita_transactions.transactions`          | NOT NULL   | Standard                                                          |
| `papita_transactions.transaction_templates` | NOT NULL   | Standard                                                          |
| `papita_transactions.account_financing`     | NOT NULL   | Standard                                                          |
| `papita_transactions.categories`            | NULLABLE   | Global seeds: `owner_id IS NULL OR owner_id = current_user`       |
| `papita_transactions.users`                 | N/A        | Policy: `id = current_user` for self-read; admin via service role |
| `*_account_details` (1:1 extensions)        | absent     | No direct RLS — access via `accounts` join or inherit FK policy   |

### 6.2 Policy template

```sql
-- Per-request: SET LOCAL app.user_id = '<uuid>';  (see §6.3)
ALTER TABLE papita_transactions.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE papita_transactions.accounts FORCE ROW LEVEL SECURITY;

CREATE POLICY accounts_tenant_select ON papita_transactions.accounts
  FOR SELECT
  USING (owner_id = current_setting('app.user_id', true)::uuid);

CREATE POLICY accounts_tenant_modify ON papita_transactions.accounts
  FOR ALL
  USING (owner_id = current_setting('app.user_id', true)::uuid)
  WITH CHECK (owner_id = current_setting('app.user_id', true)::uuid);

-- categories: read global seeds + own rows; write own rows only
CREATE POLICY categories_tenant_select ON papita_transactions.categories
  FOR SELECT
  USING (
    owner_id IS NULL
    OR owner_id = current_setting('app.user_id', true)::uuid
  );

CREATE POLICY categories_tenant_modify ON papita_transactions.categories
  FOR ALL
  USING (owner_id = current_setting('app.user_id', true)::uuid)
  WITH CHECK (owner_id = current_setting('app.user_id', true)::uuid);
```

Repeat `FOR SELECT` / `FOR ALL` pattern for `transactions`, `transaction_templates`, `account_financing`.

---

### 6.3 Service contract (when B3 is adopted)

1. FastAPI auth dependency decodes JWT → `current_user_id`
2. Before repository calls: `session.connection().execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(current_user_id)})`
3. Keep `OwnedTableRepository` filters — RLS is **additive**, not a replacement ([`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3))
4. Migrations / backfill: use `SUPABASE_SERVICE_ROLE_KEY` or direct Postgres role that bypasses RLS
5. Alembic revision series: `V4-13` or dedicated RLS migration in [#34](https://github.com/Elmorralito/save-ma-money/issues/34)

### 6.4 v4 extension tables (future)

When v4 ships, extend policies to: `budgets`, `budget_allocations`, `transaction_splits`, `counterparties`, `categorization_rules`, `account_reconciliations`, `reconciliation_items`, `transaction_attachments`, `import_batches`, `tags` — full list in [`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3).

---

## Deliverables

- [x] Decision record: chosen B0–B3 with pros/cons
- [x] `DATABASE_URL` format for Supabase pooler (transaction vs session mode)
- [x] Env var documentation: `DATABASE_URL`, `JWT_SECRET_KEY`, optional `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (NFR-05)
- [x] FastAPI integration notes: session DI via `SQLDatabaseConnector`, health checks, CORS
- [x] Auth implications for B2/B3 tied to FR-10, FR-11 (Track E in #28)
- [x] RLS policy outline for B3 (Alembic SQL migrations in #34)
- [x] `.env.example` template (do not commit secrets)

## Open items (explicitly deferred)

| Item                              | Gate / issue                                                                                                                  | Notes                                                                                                                                   |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| G1 v3 schema freeze               | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) / [#32](https://github.com/Elmorralito/save-ma-money/issues/32) | Tenancy in §1.6 / v3 §3.2; RLS in §6 — **proposed**, not maintainer-approved                                                            |
| G5 auth contract                  | Track E                                                                                                                       | `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` — blocks `/auth/*` in #25                                                      |
| G7 maintainer sign-off            | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)                                                                 | Confirm B0+B1 on #28; [#31](https://github.com/Elmorralito/save-ma-money/issues/31) deliverables complete — issue may close on PR merge |
| B2 Supabase Auth                  | G7 phase 2                                                                                                                    | Re-evaluate after G5                                                                                                                    |
| B3 RLS implementation             | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)                                                                 | SQL migrations only; no policies in this PR                                                                                             |
| `UsersService.verify_credentials` | #25 / G5                                                                                                                      | Code change out of scope                                                                                                                |
| `DATABASE_URL_MIGRATIONS` split   | PPT-039 [#49](https://github.com/Elmorralito/save-ma-money/issues/49)                                                         | Direct URL for Alembic vs pooler for API; see [`docs/ops/b1-supabase-deploy-checklist.md`](../ops/b1-supabase-deploy-checklist.md)      |
| FastAPI `main.py` + routers       | [#25](https://github.com/Elmorralito/save-ma-money/issues/25)                                                                 | Implementation blocked on G1                                                                                                            |

## References

- `modules/api/src/papita_txnsapi/config/settings.py`
- `modules/api/src/papita_txnsapi/core/security.py`
- `modules/model/src/papita_txnsmodel/database/connector.py`
- `modules/model/src/papita_txnsmodel/services/users.py`
- `docker/database/docker-compose.yml`
- Migrations: [#34](https://github.com/Elmorralito/save-ma-money/issues/34)
- Env template: [`.env.example`](../../.env.example)
