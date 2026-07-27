# Issue briefs — PPT-031 / PPT-032 program

Canonical in-repo copies of GitHub issue bodies and decision briefs for the Papita simplify + API MVP program.

**New GitHub issues:** use the chooser templates under [`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/) — epic (`01-epic.md`), program issue (`02-program-issue.md`), child under epic (`03-child-issue.md`), bug (`04-bug-report.md`). Shape references: [#42](https://github.com/Elmorralito/save-ma-money/issues/42), [#52](https://github.com/Elmorralito/save-ma-money/issues/52), [#89](https://github.com/Elmorralito/save-ma-money/issues/89), [#93](https://github.com/Elmorralito/save-ma-money/issues/93), children of #42.

Live issue status (open/closed, closing PR summaries) is mirrored in the root [CHANGELOG.md](../../CHANGELOG.md), updated by the [Auto Updates](../../.github/workflows/auto-updates.yml) workflow.

**Operator / design SSOT (not duplicated here):**

| Doc                                                        | Role                                                   |
| ---------------------------------------------------------- | ------------------------------------------------------ |
| [`modules/api/README.md`](../../modules/api/README.md)     | API reference, setup, endpoint catalog                 |
| [`docs/design/ARCHITECTURE.md`](../design/ARCHITECTURE.md) | Design body (schema, mapping, auth Part VI, migration) |
| [`docs/design/README.md`](../design/README.md)             | Design program index + gates                           |
| [`environments/README.md`](../../environments/README.md)   | `PAPITA_ENV` / secrets layout                          |

## Table of contents

| Part                                                    | Topic                                       | Issue                                                         | Status                         |
| ------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------- | ------------------------------ |
| [I](#part-i--ppt-031-simplify-requirements-28)          | PPT-031 simplify requirements               | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) | Closed                         |
| [II](#part-ii--ppt-031-c-supabase--fastapi-decision-31) | Supabase × FastAPI decision (G7 Auth-first) | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) | Complete (G7 superseded)       |
| [III](#part-iii--ppt-032-api-epic-42)                   | FastAPI MVP epic body                       | [#42](https://github.com/Elmorralito/save-ma-money/issues/42) | Open (children #43–#50 closed) |
| [IV](#part-iv--ppt-039-supabase-auth-reissue-49)        | Supabase Auth reissue                       | [#49](https://github.com/Elmorralito/save-ma-money/issues/49) | Closed                         |
| [V](#part-v--ppt-043-redis-integration-83)              | Redis integration brief                     | [#83](https://github.com/Elmorralito/save-ma-money/issues/83) | Open (post-MVP)                |
| [VI](#part-vi--ppt-045-uvicorn-process-packaging-93)    | Uvicorn process packaging                   | [#93](https://github.com/Elmorralito/save-ma-money/issues/93) | Closed                         |

**Merged sources (removed):** `PPT-031-simplify-requirements.md`, `PPT-031-C-supabase-decision-brief.md`, `_gh_body_PPT-032-epic.md`, `_gh_body_PPT-039.md`, `PPT-039-supabase-auth-reissue.md`, `PPT-043-redis-integration-brief.md`, `PPT-045-uvicorn-process-packaging-brief.md` — content lives in this README only.

**Merged into design SSOT:** PPT-044 (#89) → [`docs/design/ARCHITECTURE.md` Part VIII](../design/ARCHITECTURE.md#part-viii--post-mvp-api-hardening-ppt-044-89) + [`docs/design/README.md` § Ops](../design/README.md#ops-redis--optional-b1-pooler). PPT-045 (#93) technical packaging → [`docs/design/ARCHITECTURE.md` Part IX](../design/ARCHITECTURE.md#part-ix--uvicorn-process-packaging-ppt-045-93).

CI and local validation: [root README § Continuous integration](../../README.md#continuous-integration).

---

## Part I — PPT-031 simplify requirements (#28)

> Closed design-program requirements (FR/NFR). Historical issue body for [#28](https://github.com/Elmorralito/save-ma-money/issues/28).
> Operator docs: [`modules/api/README.md`](../../modules/api/README.md) · design: [`../design/ARCHITECTURE.md`](../design/ARCHITECTURE.md) · API epic: [#42](https://github.com/Elmorralito/save-ma-money/issues/42).

### Document ↔ issue registry

| Document                                                                                                                                     | Issue                                                                 | Track            | Status                  |
| -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------- | ----------------------- |
| [Part I (this section)](#part-i--ppt-031-simplify-requirements-28)                                                                           | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)         | Epic             | Closed                  |
| [`../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30) | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)         | A — v0 audit     | Delivered               |
| [Part II](#part-ii--ppt-031-c-supabase--fastapi-decision-31)                                                                                 | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)         | B — Supabase     | Complete (G7 supersede) |
| `../design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32` _(planned)_                                                          | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | A — v1–v3 schema | Pending                 |
| `../design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33` _(planned)_                                                             | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)         | C — API spec     | Pending                 |
| `../design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34`                                                                         | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)         | D — Migration    | **Written (v0)**        |
| `../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` _(planned)_                                                               | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E | Auth             | Pending                 |

**Related issues:** [#24](https://github.com/Elmorralito/save-ma-money/issues/24) tenancy · [#25](https://github.com/Elmorralito/save-ma-money/issues/25) API impl · [#17](https://github.com/Elmorralito/save-ma-money/issues/17) superseded · [#11](https://github.com/Elmorralito/save-ma-money/issues/11) versioning

---

### Executive summary

This issue is **phase 2 of PPT-031**. Phase 1 shipped in [#26](https://github.com/Elmorralito/save-ma-money/issues/26) via [PR #27](https://github.com/Elmorralito/save-ma-money/pull/27): a `users` table, password hashing utilities, and an `owner_id` column on nearly every entity.

Phase 2 does **not** add users again. It **simplifies** what phase 1 added, normalizes the schema toward **Third Normal Form (3NF)**, resolves open questions from [#24](https://github.com/Elmorralito/save-ma-money/issues/24) (per-user finance isolation), adopts **PostgreSQL via Supabase** as the sole database platform, documents **Supabase × FastAPI** integration, and realigns the API specification so [#25](https://github.com/Elmorralito/save-ma-money/issues/25) can implement endpoints against a stable domain model.

> **Platform decision (2026-07-02):** **DuckDB is out of scope.** All migrations, validation, and local dev target **PostgreSQL** (Docker Postgres locally; Supabase for hosted/staging). See [#34](https://github.com/Elmorralito/save-ma-money/issues/34). [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) is superseded.

**This issue is design-first.** Implementation PRs should follow sub-issues derived from the tracks below.

---

### Validation review (2026-07-02)

A second pass against the live codebase identified **gaps not fully covered** in the initial issue body. These are incorporated below as pain points **#7–#15**, **Tracks E–F**, and **FR-10–FR-17 / NFR-08–NFR-12**.

#### Highest-risk gaps (must resolve before #25)

| Priority | Gap                                                                                                            | Impact if ignored                                |
| -------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| P0       | Auth not wired (`AuthSecurityManager` has no credential verifier; `PasswordManagerFactory` never bootstrapped) | Register/login will fail at runtime              |
| P0       | `TypesDTO` deterministic IDs ignore `owner_id` + global unique `name`                                          | Cross-tenant type ID collisions                  |
| P0       | API spec fields absent from model (`balance`, `currency`, `category_type`, `transaction_type`, etc.)           | Phantom columns or broken endpoints              |
| P1       | Pre-user PostgreSQL data: `owner_id NOT NULL` migrations without backfill                                      | `./bin/alembic.sh upgrade` fails on legacy dumps |
| P1       | `/reports/*` in spec with no read-model strategy                                                               | MVP item #5 cannot be implemented                |
| P1       | Dual API specs (`API_Endpoints.md.md` + `API_Documentation.md.md`)                                             | Implementers follow conflicting sources          |
| P2       | Package version drift ([#11](https://github.com/Elmorralito/save-ma-money/issues/11))                          | v3 model/API releases out of sync                |
| P2       | CI has no Alembic PostgreSQL gate                                                                              | Schema regressions ship undetected               |

#### Sub-issues (created)

| Track            | GitHub issue                                                  |
| ---------------- | ------------------------------------------------------------- |
| A — v0 audit     | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) |
| A — v1–v3 schema | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) |
| B — Supabase     | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) |
| C — API spec     | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) |
| D — Migration    | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |

---

### Current state (developer baseline)

#### What exists today

| Layer             | Status                                                      | Key paths                                                                                                             |
| ----------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Data model**    | Production-ready ingestion pipeline                         | `modules/model/src/papita_txnsmodel/`                                                                                 |
| **Schema**        | PostgreSQL via Supabase (DuckDB deprecated)                 | `modules/model/src/papita_txnsmodel/database/connector.py`                                                            |
| **Migrations**    | Alembic                                                     | `modules/model/alembic/versions/`                                                                                     |
| **Load handlers** | In model module (registrar module not in current workspace) | `modules/model/src/papita_txnsmodel/handlers/`                                                                        |
| **API**           | Spec + partial scaffold                                     | `modules/api/API_Endpoints.md.md`; implemented: `settings.py`, `security.py` only — no `main.py`, routers, or schemas |
| **Supabase**      | **Not integrated**                                          | No client, auth, or RLS in repo                                                                                       |

#### Table inventory (`papita_transactions` schema)

| Table                            | Purpose                                                 |
| -------------------------------- | ------------------------------------------------------- |
| `users`                          | Tenant root; username, email, password                  |
| `accounts`                       | Named financial account shell (tags, start/end dates)   |
| `types`                          | Classification (ASSETS / LIABILITIES / TRANSACTIONS)    |
| `accounts_indexer`               | Polymorphic hub linking account → type → subtype row(s) |
| `assets_accounts`                | Base asset financial attributes                         |
| `banking_asset_accounts`         | Bank-specific asset extension                           |
| `real_estate_asset_accounts`     | Property asset extension                                |
| `trading_asset_accounts`         | Investment asset extension                              |
| `liability_accounts`             | Base liability financial attributes                     |
| `bank_credit_liability_accounts` | Loan/mortgage extension                                 |
| `credit_card_liability_accounts` | Credit card extension                                   |
| `financed_asset_accounts`        | Join: asset ↔ bank credit (with `financing_share`)      |
| `identified_transactions`        | Recurring/planned transaction templates                 |
| `transactions`                   | Posted money movements between accounts                 |

#### Relationship sketch

```
users
  └── owner_id on ~13 tables (added in PR #27)
accounts (owner_id)
  └── accounts_indexer (owner_id, type_id, 8 nullable subtype FKs)
        ├── assets_accounts | liability_accounts
        ├── banking_asset_accounts | real_estate_asset_accounts | trading_asset_accounts
        └── bank_credit_liability_accounts | credit_card_liability_accounts
identified_transactions (owner_id, type_id)
  └── transactions (owner_id, optional from/to account FKs)
types (nullable owner_id — global or user-scoped)
```

#### What PR #27 and PR #29 changed

- **PR #27:** `users` model, `owner_id` on all entities, extended `BaseRepository` tenant filtering, hash utilities, 4 Alembic migrations.
- **PR #29:** API documentation (`API_Endpoints.md.md`, `API_Documentation.md.md`), `Settings` with `DATABASE_URL` + JWT config, `AuthSecurityManager`. **No FastAPI app, routers, schemas, or live endpoints.**

#### Known pain points (with code references)

1. **`AccountsIndexer` sparse FK matrix** — 8 nullable FK columns route to subtype tables (`modules/model/src/papita_txnsmodel/model/indexers.py`). DTO validation in `access/indexers/dto.py` is complex and error-prone.

2. **Redundant `owner_id`** — Example: `transactions.owner_id` is stored directly, but ownership could be derived via `from_account_id → accounts.owner_id`. Same pattern on asset/liability subtype tables.

3. **API ↔ model vocabulary mismatch** — API spec defines `/categories/*`, `/budgets/*`, `/movements/*`. Model has `types`, no budgets table, and `transactions` (not "movements").

4. **Auth field mismatch** — API register expects `full_name`; model `Users` has `username`, not `full_name` (`modules/model/src/papita_txnsmodel/model/users.py` vs `API_Endpoints.md.md`).

5. **Legacy dual-dialect code** — Connector and upsert layers still reference DuckDB; PPT-031 standardizes on PostgreSQL/Supabase only ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)). [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) is **superseded**.

6. **Model doc drift** — e.g. `LiabilityAccounts` docstring references `account_id`/`type_id` fields that do not exist on the model; `users.py` TYPE_CHECKING imports `Assets` but the class is `AssetAccounts`.

7. **Auth stack incomplete** — `AuthSecurityManager.authenticate_and_get_token()` requires a `verify_credentials` callback, but `UsersService` only exposes `get_owner()` — no login/register/verify path. `UsersDTO._serialize()` calls `PasswordManagerFactory.password_manager` without ever calling `get_password_manager(keyword="argon2")` first (`access/users/dto.py`, `utils/hashutils.py`).

8. **Login identity undefined** — API login form uses field `username` with example `user@example.com`, but model separates `username` (min 6 chars, unique) and `email` (unique). Which field authenticates?

9. **Token lifecycle unspecified** — Spec defines `/auth/refresh` and `/auth/logout`, but JWT is stateless HS256 with no refresh token pair or revocation store (`token_salt` was removed in migration `ccaa69123f7e`).

10. **Types identity collision** — `TypesDTO._normalize_model()` hashes `name + classification` only (ignores `owner_id`), while `types.name` is globally unique. Two users creating "Groceries" collide on UUID and violate uniqueness.

11. **API phantom fields** — Spec accounts expose `balance`, `currency`, `initial_balance`; categories use `category_type: income|expense`, `parent_id`, hierarchy; transactions use `transaction_type`, `category_id`, `status`, `currency` — none exist on current SQLModel tables.

12. **`AccountsIndexer` skips `BaseSQLModel`** — Indexer table has no `active`, `deleted_at`, `created_at`, `updated_at` (FR-06 gap on the central hub table).

13. **Legacy data migration** — Migration `06b97dfcb5c7` adds `owner_id NOT NULL` to ~13 tables without default user seed/backfill. Pre-#26 PostgreSQL dumps cannot upgrade without manual intervention. Handlers still accept `owner=None` on load (`handlers/base.py`).

14. **Reports without read model** — Five `/reports/*` endpoints (`spending`, `budget-performance`, `cash-flow`, `trends`, `export`) have no aggregation layer; `budget-performance` depends on budgets model that does not exist.

15. **Tooling gaps** — No `.env.example` despite required `JWT_SECRET_KEY`; CI runs pytest/pre-commit but no Alembic upgrade gate on PostgreSQL; package versions diverge (model `0.1.13a28`, API `0.0.3a14`, root `v0.0.1`) — see [#11](https://github.com/Elmorralito/save-ma-money/issues/11).

---

### Goal

Deliver a **frozen v3 target schema** (3NF), a **tenancy strategy** (closing #24), a **Supabase integration decision**, and a **revised API resource map** — so #25 can implement CRUD without rework.

---

### Work tracks

#### Track A — Audit and 3NF redesign

##### Step A1: v0 audit document

Create `docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30` covering:

- Every table: columns, PKs, FKs, indexes
- Normalization analysis per table (1NF / 2NF / 3NF violations)
- Query patterns used by repositories and handlers
- Impact on registrar load pipeline

##### Step A2: v1 target schema draft

Propose concrete structural changes. Example directions (pick and justify in the doc):

| Current pattern                                 | Possible simplification                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| `accounts` + `accounts_indexer` + subtype table | Single `accounts` row with `account_kind` enum + optional extension table (1:1) |
| 8 nullable FKs on indexer                       | Typed discriminator + one FK to extension                                       |
| `owner_id` on every child                       | Scope via `accounts.owner_id` or materialized view for hot queries              |
| `identified_transactions` + `transactions`      | Keep split (template vs posted) or merge with `is_template` flag                |

##### Step A3: v2 after API domain review

Incorporate API naming decisions (categories, budgets, movements) into the schema.

##### Step A4: v3 freeze

Final ER diagram in `docs/`, Alembic migration outline, and explicit list of **intentional denormalizations** (if any) with measured rationale.

**Gate:** No API CRUD implementation in #25 until v3 is approved in a comment on this issue.

---

#### Track B — Supabase × FastAPI (primary database platform)

**Target platform:** PostgreSQL via **Supabase**. DuckDB is **not** a supported deployment or validation target for PPT-031.

The repo uses **SQLModel + SQLAlchemy** with `DATABASE_URL`. This track produces a **decision record** for Supabase integration and FastAPI wiring.

##### Options to evaluate

| Option                          | Description                                              | Code impact                                                     |
| ------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| **B0 — Local Postgres**         | Docker Postgres for local dev; Supabase for staging/prod | `DATABASE_URL` env docs; same Postgres dialect everywhere       |
| **B1 — Supabase Postgres only** | All environments use Supabase pooler connection string   | Env config + connection string docs                             |
| **B2 — Supabase Auth**          | Replace/bridge JWT auth with Supabase Auth               | Map `auth.users.id` ↔ `papita_transactions.users.id`            |
| **B3 — Supabase Auth + RLS**    | DB-enforced tenant isolation                             | PostgreSQL RLS policies on `owner_id`; Alembic SQL for policies |

##### FastAPI integration points (regardless of option)

| Component               | Current state                                    | Expected work                                               |
| ----------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| `Settings.DATABASE_URL` | Validates via `SQLDatabaseConnector.establish()` | Session dependency for routes                               |
| `AuthSecurityManager`   | JWT generate/decode                              | Login/register routes; optional Supabase token validation   |
| `main.py` / routers     | Empty files                                      | App factory, `/api/v1` router mount, CORS                   |
| Health endpoints        | Spec only                                        | Probe DB with `SELECT 1` or connector health check          |
| Tenant scoping          | `BaseRepository` patterns in model               | API dependency injects `current_user_id` into service calls |

**Default recommendation to document:** **B0 or B1** until v3 schema is frozen (Postgres everywhere). Defer B2/B3 to avoid rewriting auth mid-refactor (PR #27 already invested in `Users` + local JWT). **Do not evaluate DuckDB paths.**

---

#### Track C — API spec realignment

Before implementing [#25](https://github.com/Elmorralito/save-ma-money/issues/25), update `modules/api/API_Endpoints.md.md` so every resource maps to a v3 table/DTO.

| API spec resource | Model today                                                         | Decision required                                               |
| ----------------- | ------------------------------------------------------------------- | --------------------------------------------------------------- |
| `/categories/*`   | `types` (`TypesClassifications`: ASSETS, LIABILITIES, TRANSACTIONS) | Rename API to `/types/*` or expose `/categories` as alias       |
| `/transactions/*` | `transactions` + optional `identified_transaction_id`               | Document whether templates are nested or separate resource      |
| `/movements/*`    | No `movements` table; likely `transactions` with from/to accounts   | Define domain term; merge into `/transactions` or add view      |
| `/budgets/*`      | **No model**                                                        | Add `budgets` + allocation tables in v3 **or** remove from spec |
| `/auth/register`  | `Users`: `username`, `email`, `password`                            | Align request body (`full_name` vs `username`)                  |

**MVP endpoint order for #25 (after v3 freeze):**

1. `GET /health`, `GET /health/ready`, `GET /health/live`
2. `POST /auth/register`, `POST /auth/login`
3. `/accounts/*` CRUD
4. `/transactions/*` (+ `/types/*` or renamed categories)
5. `GET /reports/*` (read-only aggregates)
6. Defer budgets and movements until model support exists

---

#### Track D — Migration and validation (PostgreSQL / Supabase)

**Database platform:** PostgreSQL via Supabase. **DuckDB is out of scope** for PPT-031 (see [#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

- Write Alembic migrations for v3 (PostgreSQL dialect; expect a new migration series after PR #27's four migrations).
- Provide backfill SQL/scripts for `accounts_indexer` → simplified account structure.
- **FR-14:** Legacy `owner_id` backfill for pre-#26 PostgreSQL data (default user seed or documented wipe-and-reload).
- Run regression on model handlers and `modules/model/tests/`.
- Validate `./bin/alembic.sh upgrade` on **Docker Postgres** and **Supabase** connection strings.
- Regenerate PostgreSQL ER diagram. [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) is **superseded** by this platform decision.

---

#### Track E — Auth & security contract (prerequisite for #25 MVP)

Define the auth layer end-to-end before implementing `/auth/*` routes.

| Topic            | Current state                                             | Decision needed                                 |
| ---------------- | --------------------------------------------------------- | ----------------------------------------------- |
| Registration     | Spec: `full_name`; model: `username`, `email`, `password` | Unified register schema + response              |
| Login identifier | Form field `username` with email example                  | Login by email, username, or both               |
| Password hashing | Argon2 via `PasswordManagerFactory` (uninitialized)       | Bootstrap in app lifespan / settings            |
| JWT `sub` claim  | String user id in token                                   | Document: UUID string from `Users.id`           |
| Refresh / logout | Spec endpoints exist                                      | Stateless JWT only, or refresh token + denylist |
| API dependencies | Missing `python-multipart` for OAuth2 form login          | Add to `modules/api/pyproject.toml`             |

**Deliverable:** `docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` covering FR-10, FR-11.

---

#### Track F — Reports & read models

The API spec lists read-only reports that require aggregation, not CRUD tables.

| Endpoint                          | Depends on                      | v3 decision               |
| --------------------------------- | ------------------------------- | ------------------------- |
| `GET /reports/spending`           | transactions + categories/types | SQL/view spec             |
| `GET /reports/budget-performance` | budgets (missing)               | Defer or add budget model |
| `GET /reports/cash-flow`          | accounts + transactions         | SQL/view spec             |
| `GET /reports/trends`             | time-series aggregates          | SQL/view spec             |
| `GET /reports/export`             | all above                       | Format + scope            |

**Deliverable:** Read-model strategy in v3 doc (materialized views, service-layer queries, or deferred from MVP). Update MVP list: reports may ship as stubs returning 501 until queries defined.

---

### Functional requirements (with explanations)

#### FR-01 — Target schema satisfies Third Normal Form (3NF)

**Requirement:** The v3 schema must satisfy 3NF unless a specific exception is documented with query-performance or domain-clarity justification.

**Why:** The current schema grew organically (indexer pattern from [PR #12 / PPT-022](https://github.com/Elmorralito/save-ma-money/pull/12), users from PR #27). Normalization reduces update anomalies (e.g. changing `owner_id` in one place vs. 13), simplifies the PostgreSQL FK graph, and makes API DTOs predictable.

**Developer notes:**

- **1NF:** Ensure atomic columns; `tags` as PostgreSQL `ARRAY` is acceptable if treated as atomic multi-value, but document whether tags belong in a junction table for queryability.
- **2NF:** If any table uses composite PKs, ensure no partial dependencies. Example: `financed_asset_accounts` uses composite PK `(bank_credit_liability_account_id, asset_account_id)` — verify all non-key columns depend on the full key.
- **3NF:** Eliminate transitive dependencies. Primary candidate: redundant `owner_id` on child tables when `owner_id` is derivable through FK chains (`transactions → accounts → users`).

**Acceptance:** v0 audit lists each violation; v3 doc lists each resolved violation or documented exception.

---

#### FR-02 — Multi-tenant isolation strategy (resolves #24)

**Requirement:** Define and implement one consistent strategy so User A cannot read or mutate User B's financial data.

**Why:** [#24](https://github.com/Elmorralito/save-ma-money/issues/24) asked for per-user finance isolation. PR #27 added `owner_id` everywhere but did not decide whether redundancy is intentional, whether `types` can be global (`owner_id` nullable), or whether isolation is enforced in the app layer vs. database RLS.

**Developer notes — choose one strategy and document it:**

| Strategy                        | Mechanism                                                                    | Pros                                  | Cons                                                      |
| ------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------- | --------------------------------------------------------- |
| **A — FK chain**                | Filter via `accounts.owner_id`; drop redundant child `owner_id`              | Fewer columns; single source of truth | Joins required for direct transaction queries             |
| **B — Denormalized `owner_id`** | Keep `owner_id` on hot tables; enforce consistency via triggers or app layer | Faster tenant-filtered queries        | Update anomalies if account ownership changes             |
| **C — RLS (Supabase/Postgres)** | Policy: `owner_id = current_setting('app.user_id')`                          | DB-enforced; defense in depth         | Requires Supabase/Postgres; aligns with platform decision |

**Acceptance:** Decision recorded in v3 doc; `BaseRepository` and API dependencies implement the chosen strategy; cross-tenant denial test cases listed.

---

#### FR-03 — Simplify or eliminate `AccountsIndexer`

**Requirement:** Remove `AccountsIndexer` or reduce it to at most one optional extension FK plus an explicit type discriminator.

**Why:** `AccountsIndexer` (`indexers.py`) holds 8 nullable FKs (`asset_account_id`, `liability_account_id`, `banking_asset_account_id`, etc.). Only one should be populated per row, but nothing in the DB enforces that. Repository and DTO code must infer the active subtype manually.

**Developer notes:**

- Preferred patterns: **single-table inheritance** with nullable subtype columns on `accounts`, **class table inheritance** with one 1:1 extension table keyed by `account_id`, or **JSONB extension blob** for rarely queried subtype fields (document 3NF exception if used).
- Migration must map existing indexer rows to the new structure without data loss.
- Update `modules/model/src/papita_txnsmodel/services/indexers.py`, `services/extends.py` (`TypedLinkedEntitiesServiceMixin`), `handlers/factory.py`, and load handlers that depend on indexer resolution.

**Acceptance:** v3 ER diagram has no 8-FK sparse matrix; indexer service removed or reduced to trivial lookup.

---

#### FR-04 — Account subtypes without subtype table explosion

**Requirement:** Banking, real estate, trading, bank credit, and credit card accounts must remain representable without requiring six separate physical tables unless each adds substantial non-overlapping columns.

**Why:** Today there are separate tables for each subtype (`banking_asset_accounts`, `real_estate_asset_accounts`, etc.) with overlapping financial columns duplicated from base `assets_accounts` / `liability_accounts`. This increases join complexity and migration cost.

**Developer notes:**

- Audit column overlap across subtype tables in `assets.py` and `liabilities.py`.
- If overlap exceeds ~70%, consolidate shared columns into base table; keep extension tables only for truly unique fields (e.g. `RealEstateAssetAccountsAreaUnits`, `financing_share`).
- Preserve enum types in `enums.py` for domain clarity.

**Acceptance:** v3 table list with column justification per subtype; fewer joins required for "list all accounts for user" query.

---

#### FR-05 — Clear semantics for `IdentifiedTransactions` vs `Transactions`

**Requirement:** Document and model the relationship between transaction templates (`identified_transactions`) and posted transactions (`transactions`).

**Why:** `IdentifiedTransactions` holds planned name, value, day-of-month, and `type_id`. `Transactions` holds actual `value`, `transaction_ts`, and optional `from_account_id` / `to_account_id`. The API spec uses "transactions" and "movements" without mapping to these concepts — developers will build the wrong endpoints without clarity.

**Developer notes:**

- Decide: **keep two tables** (budget/recurring template vs ledger entry) or **unify** with `status` / `is_posted` discriminator.
- If kept separate: API should expose `/identified-transactions/*` or nest under accounts; `/movements/*` should not duplicate `/transactions/*` without definition.
- FK: `transactions.identified_transaction_id` is optional — document when it must be set (e.g. recurring match) vs. ad-hoc transactions.

**Acceptance:** Domain glossary in design doc; ER diagram shows cardinality; API spec updated accordingly.

---

#### FR-06 — Preserve soft delete and audit fields

**Requirement:** All user-facing entities must retain `active`, `deleted_at`, `created_at`, and `updated_at` via `BaseSQLModel`.

**Why:** The ingestion pipeline and repositories rely on soft delete (`soft_delete_records()`) and conflict resolution. Removing these fields would break registrar reload semantics.

**Developer notes:**

- Inherited from `modules/model/src/papita_txnsmodel/model/base.py`.
- Any new v3 tables must extend `BaseSQLModel`, not raw `SQLModel`.
- **`AccountsIndexer` today uses raw `SQLModel`** — if retained temporarily, migrate to `BaseSQLModel` or document explicit exclusion with rationale.
- API DELETE endpoints should call soft delete, not hard delete, unless admin-only hard delete is explicitly spec'd.

**Acceptance:** v3 schema checklist confirms all user-facing tables extend `BaseSQLModel` patterns.

---

#### FR-07 — API resources map 1:1 to v3 model before #25 CRUD work

**Requirement:** Every endpoint in `API_Endpoints.md.md` must map to a v3 DTO/table, or be removed from the spec.

**Why:** PR #29 added a rich API spec (43+ operations) but the model does not support budgets, uses different naming, and routers are empty. Implementing against the current spec will produce orphan endpoints or phantom tables.

**Developer notes:**

- Produce a mapping table: `Endpoint → Router → Service → Repository → DTO → SQLModel`.
- Flag breaking renames early (categories → types).
- Align auth request/response shapes with `Users` model fields.

**Acceptance:** `docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33` reviewed and linked from this issue; #25 scoped to MVP list only.

---

#### FR-08 — Registrar pipeline compatibility

**Requirement:** The registrar/load handlers must continue to ingest data, or a documented migration path must exist for each breaking schema change.

**Why:** The monorepo's primary production path is registrar → handlers → services → DB (`modules/registrar/`, `modules/model/src/papita_txnsmodel/handlers/`). A simplified schema is useless if CSV/plugin loads break silently.

**Developer notes:**

- Trace handlers: `handlers/base.py`, `handlers/transactions.py`, indexer services.
- For each v3 breaking change, specify: handler update, DTO update, backfill script, or deprecation period.
- Run existing tests in `modules/model/tests/` and registrar tests after migration.

**Acceptance:** Checklist of affected handlers with owner; green test run on sample load after v3 migration applied locally.

---

#### FR-09 — Resolve budgets in model or API spec

**Requirement:** Either add first-class budget entities to v3, or remove `/budgets/*` from the API specification.

**Why:** `API_Endpoints.md.md` defines full CRUD for budgets, allocations, and budget summaries. There is **no** `budgets` table in the model. This is the largest spec-vs-model gap.

**Developer notes:**

- If adding budgets: typical model is `budgets` (period, owner_id) + `budget_allocations` (category/type_id, amount) + optional link to `identified_transactions`.
- If deferring: mark `/budgets/*` as "v2 API" in spec and exclude from #25 MVP.
- Do not implement budget endpoints against a non-existent table.

**Acceptance:** Explicit decision in v3 doc; spec updated; #25 MVP excludes budgets if deferred.

---

#### FR-10 — Auth credential verification & identity mapping

**Requirement:** Define and implement the contract between API auth routes, `AuthSecurityManager`, and `UsersService`/`UsersDTO`.

**Why:** JWT generation exists but credential verification is not wired. Register cannot hash passwords without initializing `PasswordManagerFactory`. Login field semantics (email vs username) are undefined.

**Developer notes:**

- Add `UsersService.verify_credentials(username_or_email, password) -> UsersDTO | None`.
- Bootstrap `PasswordManagerFactory.get_password_manager(keyword="argon2")` at API startup.
- Document JWT `sub` as the string form of `Users.id` (deterministic uuid5 from username hash today).
- Align `POST /auth/register` request body with `UsersDTO` validators (`USERNAME_REGEX`, `PASSWORD_REGEX`).

**Acceptance:** Auth contract doc merged; register/login sequence diagram; fields mapped in API spec.

---

#### FR-11 — JWT refresh, logout, and revocation strategy

**Requirement:** Document how `/auth/refresh` and `/auth/logout` behave, or remove them from MVP spec.

**Why:** Stateless HS256 tokens cannot be invalidated on logout without a denylist, rotation, or refresh-token pair. Spec promises behavior the stack cannot deliver today.

**Developer notes:**

- **Option A:** MVP = access token only; remove refresh/logout from MVP or return 501 with doc note.
- **Option B:** Short-lived access + refresh token stored server-side or in httpOnly cookie.
- **Option C:** Supabase Auth (Track B) owns session lifecycle.

**Acceptance:** Decision recorded; spec updated; #25 MVP scope matches chosen option.

---

#### FR-12 — Reports read-model strategy

**Requirement:** Define how `/reports/*` endpoints derive data without new normalized tables unless justified.

**Why:** Reports are read aggregations over transactions, accounts, types, and budgets. No report tables exist; MVP lists reports as item #5 but provides no query design.

**Developer notes:**

- Prefer service-layer queries or SQL views over duplicating data in report tables.
- `budget-performance` blocked until FR-09 budgets decision.
- Document pagination, date filters, and tenant scoping for each report.

**Acceptance:** Report query spec in design doc; MVP report endpoints scoped (full vs stub vs defer).

---

#### FR-13 — Category taxonomy mapping

**Requirement:** Resolve semantic gap between API categories and model `Types`.

**Why:** API uses `category_type: income|expense`, hierarchical `parent_id`, and subcategories. Model uses flat `Types` with `TypesClassifications: ASSETS|LIABILITIES|TRANSACTIONS` and globally unique `name`. Renaming `/categories` → `/types` alone is insufficient.

**Developer notes:**

- Map domain concepts explicitly (e.g. expense categories = `Types` where `classification=TRANSACTIONS`).
- Decide if hierarchy requires `parent_id` on `types` or a separate taxonomy table.
- Resolve conflict with FR-15 type identity rules.

**Acceptance:** Taxonomy mapping table in API-model mapping doc; v3 schema change list if hierarchy added.

---

#### FR-14 — Legacy data & tenant assignment migration

**Requirement:** Document and implement migration path for pre-user databases and loads with `owner=None`.

**Why:** PR #27 migrations add `owner_id NOT NULL` without backfill. Handlers still allow ownerless loads. Developers with existing pre-#26 PostgreSQL dumps hit upgrade failures.

**Developer notes:**

- Options: seed a `default` system user and backfill; require wipe-and-reload for dev; reject ownerless loads in handlers.
- Include in Track D migration scripts, not only indexer backfill.
- Document in README breaking-change notice for PPT-031.

**Acceptance:** Migration runbook with before/after steps; test upgrade from pre-#26 PostgreSQL snapshot (or documented wipe-and-reload).

---

#### FR-15 — Types global vs user-scoped identity rules

**Requirement:** Define uniqueness, ID generation, and write scoping for `types` (`owner_id` nullable).

**Why:** `TypesDTO` generates deterministic IDs without `owner_id`, but `types.name` is globally unique. `TypesRepository` read path merges global + owned types; write path scoping is weaker than `OwnedTableRepository`. User deletion cascade on `owned_types` vs global types is undefined.

**Developer notes:**

- Include `owner_id` (or tenant namespace) in ID hash **or** drop global unique on `name` in favor of composite unique `(owner_id, name, classification)`.
- Align with FR-02 tenancy strategy and FR-13 taxonomy.
- Document behavior when global types exist and user is deleted.

**Acceptance:** Types identity rules in v3 doc; repository tests for two tenants creating same type name.

---

#### FR-16 — `FinancedAssetAccounts` integrity

**Requirement:** Clarify cardinality, primary key, and cross-owner constraints for financed asset joins.

**Why:** PK is only `bank_credit_liability_account_id` (one credit → one asset; one asset may have many credits). `financing_share` has no sum-to-1 constraint. Join table carries redundant `owner_id` without DB check that asset, liability, and join owners match. DTO default `financing_share=0.0` violates `gt=0`.

**Developer notes:**

- Decide composite PK `(asset_account_id, bank_credit_liability_account_id)` if many-to-many needed.
- Add CHECK constraints or service validation for owner consistency and share totals.
- Fix DTO default to satisfy validators.

**Acceptance:** ER diagram updated; constraints listed in v3 migration plan.

---

#### FR-17 — API schema layer & OpenAPI source of truth

**Requirement:** Choose a single API specification source and define Pydantic schema strategy for #25.

**Why:** Two markdown specs exist (`API_Endpoints.md.md`, `API_Documentation.md.md`) plus aspirational README structure. No `schemas/`, routers, or OpenAPI JSON. FastAPI deps missing `python-multipart` for form login.

**Developer notes:**

- Consolidate to one spec; generate or maintain OpenAPI from FastAPI app as source of truth going forward.
- Rule: API schemas in `papita_txnsapi/schemas/` map to model DTOs — no duplicate business validation logic.
- Add missing dependencies before auth routes.

**Acceptance:** Single spec file marked canonical; schema mapping rules in API README; OpenAPI export plan for #25.

---

### Non-functional requirements (with explanations)

#### NFR-01 — Alembic migrations with rollback notes

**Requirement:** All schema changes ship as Alembic revisions in `modules/model/alembic/versions/` with documented downgrade path.

**Why:** PPT-031 targets **PostgreSQL via Supabase** only. Migrations must be PostgreSQL-compatible (Supabase uses standard Postgres).

**Developer notes:**

- Name migrations with date prefix convention already in repo.
- Test: `./bin/alembic.sh upgrade` and `downgrade -1` on Docker Postgres and Supabase staging.
- Large data backfills: separate data migration script, not only DDL.
- Remove or deprecate DuckDB-specific Alembic branches in a follow-up cleanup PR (out of PPT-031 design scope).

**Acceptance:** Migration PR includes upgrade/downgrade test log in description.

---

#### NFR-02 — Local development on PostgreSQL / Supabase

**Requirement:** Simplified schema must remain developable locally using PostgreSQL tooling.

**Why:** Local dev uses Docker Postgres (`docker/database/docker-compose.yml`) or a Supabase project connection string. DuckDB file storage (`.data/store.duckdb`) is **deprecated** for this project.

**Developer notes:**

- `DATABASE_URL` must point to a PostgreSQL-compatible endpoint (Docker or Supabase pooler).
- Verify column types work on Postgres (e.g. `ARRAY`, `DECIMAL`, UUID).
- Document Supabase env vars: `DATABASE_URL`, optional `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- RLS policies (B3) apply on Supabase/Postgres; test with policy-enabled staging DB.

**Acceptance:** README or design doc "Local dev" section updated for Supabase/Postgres-only workflow.

---

#### NFR-03 — Preserve layered architecture

**Requirement:** Keep Model → Access (DTO/Repository) → Service → Handler/API separation.

**Why:** Project conventions (`.cursor/rules`, module READMEs) enforce this pattern. API routes must not embed raw SQL; they call services that use repositories.

**Developer notes:**

- New v3 entities need: SQLModel in `model/`, DTO in `access/`, repository, service, optional handler, API schema + router.
- Reuse `BaseRepository`, `BaseService`, `check_expected_dto_type()`.

**Acceptance:** Architecture review checklist in PR template for v3 implementation PRs.

---

#### NFR-04 — Cross-tenant access denial tests

**Requirement:** Automated tests must prove User A cannot access User B's records.

**Why:** Financial data isolation is a security requirement, not only a data modeling concern. PR #27 added `owner_id` but comprehensive denial tests may not cover all repositories.

**Developer notes:**

- Add integration tests: create two users, seed data, assert 404 or empty result when querying other tenant's IDs.
- If RLS: test with Postgres policy enabled.
- Cover at minimum: accounts, transactions, types.

**Acceptance:** Test module or marked test cases listed in v3 implementation PR.

---

#### NFR-05 — Secrets via environment variables only

**Requirement:** `DATABASE_URL`, `JWT_SECRET_KEY`, and any Supabase keys must load from env / `.env`, never committed.

**Why:** `Settings` in `modules/api/src/papita_txnsapi/config/settings.py` already uses `pydantic-settings` with `.env`. Supabase introduces `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — same rule applies.

**Developer notes:**

- Update `.env.example` if new vars added (do not commit real `.env`).
- Document in API README which vars are required per deployment option (B0–B3).

**Acceptance:** No secrets in diff; example env documented.

---

#### NFR-06 — Updated ER diagram and API mapping documentation

**Requirement:** Ship updated ER diagram and endpoint-to-model mapping in `docs/`.

**Why:** Existing diagram `docs/postgres_papita_transactions.png` predates users and simplification. Developers and API implementers need a single visual source of truth.

**Developer notes:**

- Regenerate Postgres ER after v3 migration on Docker.
- Add `docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33` as tabular complement to ER.

**Acceptance:** Files linked in issue comment at v3 freeze.

---

#### NFR-07 — PostgreSQL FK integrity on simplified schema

**Requirement:** v3 schema must create a complete, valid FK graph on PostgreSQL (Supabase).

**Why:** Simplifying the schema (especially removing the `AccountsIndexer` sparse FK matrix) should yield a cleaner ER diagram and reliable constraint enforcement on the sole supported platform.

**Developer notes:**

- After v3 migration, run `./bin/alembic.sh upgrade` against Docker Postgres and Supabase staging.
- Regenerate ER diagram; verify all expected FKs exist.
- Supersedes [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps — no longer applicable).

**Acceptance:** ER diagram + FK checklist attached to [#34](https://github.com/Elmorralito/save-ma-money/issues/34) migration PR.

---

#### NFR-08 — Password manager bootstrap

**Requirement:** Application startup must initialize `PasswordManagerFactory` before any `UsersDTO` serialization.

**Why:** Without `get_password_manager(keyword="argon2")`, registration raises at runtime when hashing passwords.

**Developer notes:** Wire in FastAPI lifespan or `Settings` model validator; add unit test in model or API test suite.

**Acceptance:** Test creates user via DTO serialize path without error.

---

#### NFR-09 — CI test matrix & Alembic PostgreSQL gate

**Requirement:** CI must reflect modules that exist and gate schema changes on PostgreSQL where feasible.

**Why:** Root `pyproject.toml` references `./modules/api/tests` and `./modules/registrar/tests` but only `modules/model/tests/` exists. No CI job runs `./bin/alembic.sh upgrade` on PostgreSQL.

**Developer notes:**

- Fix testpaths or add placeholder tests; add optional CI job for Alembic upgrade on Docker Postgres (and Supabase staging if secrets available).
- v3 PRs include migration test log in description until CI job exists.

**Acceptance:** CI config updated or tracking issue linked; manual gate documented for v3 migration PRs.

---

#### NFR-10 — PostgreSQL upsert behavior

**Requirement:** Document and test upsert behavior on PostgreSQL after schema changes.

**Why:** Load handlers and repositories use `PostgreSQLUpserter` for idempotent ingestion. With DuckDB deprecated, upsert tests target Postgres only.

**Developer notes:** Add integration test against Docker Postgres or document upsert SQL in v0 audit. Legacy `DuckDBUpserter` code may be removed in a separate cleanup PR.

**Acceptance:** Upsert behavior noted in design docs; regressions tested if upsert-heavy paths change.

---

#### NFR-11 — Package & repo version alignment ([#11](https://github.com/Elmorralito/save-ma-money/issues/11))

**Requirement:** v3 schema release must coordinate model and API package versions per monorepo policy.

**Why:** Model `0.1.13a28`, API `0.0.3a14`, root `v0.0.1`. API `pyproject.toml` pins published model range, not local path dep — v3 breaking changes may not propagate in CI.

**Developer notes:**

- Bump model semver for breaking schema; bump API to match.
- Document coupling rule: API depends on exact model version for v3 release train.
- Coordinate with [#11](https://github.com/Elmorralito/save-ma-money/issues/11).

**Acceptance:** Version bump plan in v3 sign-off comment; #11 referenced.

---

#### NFR-12 — Model & documentation consistency

**Requirement:** v3 refactor includes cleanup of known doc/model drift before freeze.

**Why:** Incorrect docstrings and TYPE_CHECKING imports (`Assets` vs `AssetAccounts`, `LiabilityAccounts` fields) cause unsafe refactors during simplification.

**Developer notes:** Add to v3 PR checklist: docstrings match fields; TYPE_CHECKING imports correct; interrogate/doc coverage maintained.

**Acceptance:** Known drift items from pain point #6 resolved or tracked with issue links.

---

### Issue dependencies

| Issue                                                                                                                       | Relationship                                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| [#26](https://github.com/Elmorralito/save-ma-money/issues/26)                                                               | Done — baseline for this work                                                                                                       |
| [#24](https://github.com/Elmorralito/save-ma-money/issues/24)                                                               | Close when FR-02 tenancy strategy is approved                                                                                       |
| [#25](https://github.com/Elmorralito/save-ma-money/issues/25)                                                               | Blocked until v3 schema + API mapping approved                                                                                      |
| [#17](https://github.com/Elmorralito/save-ma-money/issues/17)                                                               | **Superseded** — DuckDB deprecated; closed; Postgres FK validation in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |
| [#11](https://github.com/Elmorralito/save-ma-money/issues/11)                                                               | Coordinate version bumps at v3 release (NFR-11)                                                                                     |
| [#30](https://github.com/Elmorralito/save-ma-money/issues/30)–[#34](https://github.com/Elmorralito/save-ma-money/issues/34) | Implementation sub-issues for tracks A–D                                                                                            |

---

### Sub-issues

| ID        | GitHub                                                        | Title                                              | Track |
| --------- | ------------------------------------------------------------- | -------------------------------------------------- | ----- |
| PPT-031-A | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) | Data model audit and 3NF gap analysis (v0)         | A     |
| PPT-031-B | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) | Target schema iterations v1–v3 + ER diagram        | A     |
| PPT-031-C | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) | Supabase × FastAPI decision record                 | B     |
| PPT-031-D | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) | API spec realignment (`API_Endpoints.md.md`)       | C     |
| PPT-031-E | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) | Alembic migration + Supabase PostgreSQL validation | D     |

Tracks **E** (auth) and **F** (reports) are scoped in this issue; implement via #33 (spec) and #25 (code) after v3 freeze.

---

### Acceptance criteria (issue closure)

- [x] `docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30` merged ([#30](https://github.com/Elmorralito/save-ma-money/issues/30))
- [ ] v3 target schema approved (comment sign-off by maintainer) ([#32](https://github.com/Elmorralito/save-ma-money/issues/32))
- [ ] Tenancy strategy documented (FR-02); [#24](https://github.com/Elmorralito/save-ma-money/issues/24) ready to close
- [ ] Types identity rules documented (FR-15)
- [ ] Auth contract documented (FR-10, FR-11, Track E)
- [ ] Reports read-model strategy documented (FR-12, Track F)
- [ ] Legacy data migration runbook (FR-14)
- [ ] Supabase B0–B3 decision recorded ([#31](https://github.com/Elmorralito/save-ma-money/issues/31))
- [ ] Single canonical API spec + model mapping ([#33](https://github.com/Elmorralito/save-ma-money/issues/33), FR-07, FR-17)
- [ ] Budgets decision recorded (FR-09)
- [ ] Category taxonomy mapped (FR-13)
- [ ] Migrations validated on PostgreSQL / Supabase ([#34](https://github.com/Elmorralito/save-ma-money/issues/34))
- [ ] Version alignment plan linked to [#11](https://github.com/Elmorralito/save-ma-money/issues/11) (NFR-11)
- [ ] [#25](https://github.com/Elmorralito/save-ma-money/issues/25) unblocked with explicit MVP endpoint list

---

### References

#### GitHub

- [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — parent issue
- [#30](https://github.com/Elmorralito/save-ma-money/issues/30)–[#34](https://github.com/Elmorralito/save-ma-money/issues/34) — sub-issues
- PR [#27](https://github.com/Elmorralito/save-ma-money/pull/27) — users + `owner_id`
- PR [#29](https://github.com/Elmorralito/save-ma-money/pull/29) — API spec + scaffold

#### Repo documents

- [`docs/issues/README.md`](./README.md) — issue document index
- [`docs/design/README.md`](../design/README.md) — design document registry
- [`docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30) — [#30](https://github.com/Elmorralito/save-ma-money/issues/30)
- [`docs/issues/PPT-031-C-supabase-decision-brief.md`](#part-ii--ppt-031-c-supabase--fastapi-decision-31) — [#31](https://github.com/Elmorralito/save-ma-money/issues/31)

#### Code

- Model: `modules/model/src/papita_txnsmodel/model/`
- Indexer: `modules/model/src/papita_txnsmodel/model/indexers.py`
- API spec: `modules/api/API_Endpoints.md.md`
- Settings: `modules/api/src/papita_txnsapi/config/settings.py`
- Auth: `modules/api/src/papita_txnsapi/core/security.py`
- ER (current): `docs/postgres_papita_transactions.png`
- Alembic: `modules/model/alembic/`, `bin/alembic.sh`

---

## Part II — PPT-031-C Supabase × FastAPI decision (#31)

> B0/B1/B2/B3 platform decision + **G7 Auth-first supersede**. [#31](https://github.com/Elmorralito/save-ma-money/issues/31).

**GitHub issue:** [#31](https://github.com/Elmorralito/save-ma-money/issues/31) · **Parent:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) · **Track:** B
**Status:** Complete (2026-07-06) · **Gate G7:** **Superseded in part (2026-07-13)** — see [G7 supersede](#g7-supersede-2026-07-13--auth-first) · Original: **Proposed — B0 (local) + B1 (stg/prod Postgres); B2/B3 deferred** (awaiting sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28))

### G7 supersede (2026-07-13) — Auth-first

**Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) pivot:** MVP Supabase usage is **Auth only** (former **B2**). **Supabase-hosted Postgres (B1 pooler) is no longer an epic acceptance requirement.** Database remains Docker Postgres locally (B0) or **any** Postgres URL in staging/prod.

| Prior G7 (this brief)                             | Current epic direction                                                                        |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| B1 = required staging/prod DB via Supabase pooler | B1 DB = **optional** ops (pooler wiring may remain in tree)                                   |
| B2 = Supabase Auth deferred                       | B2 Auth = **MVP** via PPT-039 ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)) |
| Auth = local JWT on B0/B1                         | Auth = Supabase JWT verification; local HS256 issuance deprecated                             |

Canonical reissue write-up: [Part IV](#part-iv--ppt-039-supabase-auth-reissue-49). Operator API docs: [`modules/api/README.md`](../../modules/api/README.md). §2 pooler formats remain valid **if** operators choose Supabase as a Postgres host — they are not required for PPT-032 close-out.

---

### Document ↔ issue cross-reference

| Related document                                                                                                                                 | Issue                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| [`PPT-031-simplify-requirements.md`](#part-i--ppt-031-simplify-requirements-28)                                                                  | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — requirements (Track B) |
| [`../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)     | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) — v0 schema baseline     |
| [`../design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32) | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) — v3 tenancy (proposed)  |
| `../design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34` _(planned)_                                                                 | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) — RLS migrations (B3)    |
| `../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` _(planned)_                                                                   | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E — FR-10/11       |

### Executive decision

**Propose G7 as a phased B0 + B1 path:** use **Docker Postgres locally** (B0) for offline development, Alembic iteration, and CI parity; use **Supabase PostgreSQL** (B1) for staging and production via the pooler `DATABASE_URL`. Keep **local JWT + `papita_transactions.users`** (PR #27 investment) until `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` (G5) is written. **Defer B2 (Supabase Auth)** and **B3 (RLS; optional B2)** to a post-MVP phase — RLS policy outline is documented here for [#34](https://github.com/Elmorralito/save-ma-money/issues/34) but not implemented.

**Rationale:** B0/B1 share one Postgres dialect and require no auth rewrite mid-refactor. **DuckDB is not part of this path** — Postgres is the only supported engine going forward. v3 schema (proposed in [#32](https://github.com/Elmorralito/save-ma-money/issues/32)) already adopts app-layer tenancy (denormalized `owner_id`); RLS is optional defense-in-depth, not a G1 blocker.

---

### Platform decision (2026-07-02)

**DuckDB is deprecated and will not be used.** As of PPT-031 ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)), DuckDB is **no longer a supported database** for development, testing, CI, staging, or production. Do not use DuckDB connection strings, file storage (e.g. `.data/store.duckdb`), or DuckDB-specific code paths for new work.

| Status         | Detail                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Supported**  | **PostgreSQL only** — Docker Postgres locally (B0); Supabase for hosted/staging/production (B1)                                                                                |
| **Deprecated** | DuckDB file/in-memory backends, `DuckDBUpserter` (runtime rejection via `UpserterFactory`), `bin/setup_duckdb.py`, and connector fallbacks that default to `duckdb://`         |
| **Superseded** | [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) — Postgres FK validation lives in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |

Legacy DuckDB code may remain in the repo until a cleanup PR removes it; that removal is **out of scope** for this decision record. **All new configuration must use `postgresql+psycopg2://` URLs** (see §2). Legacy tooling still referencing DuckDB (not authoritative): `bin/alembic.sh` (`--duckdb-path`), `modules/model/alembic/env.py` (`AlembicDuckDBImpl`), and `SQLDatabaseConnector` fallback when `DATABASE_URL` is unset (see §4.1).

~~Former option: Self-hosted Postgres + DuckDB~~ — **removed permanently**. Do not document, evaluate, or recommend DuckDB paths.

---

### Goal

Document Supabase × FastAPI integration and produce a decision record for auth/RLS options — **not full implementation** until v3 schema is frozen ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)).

---

### 1. Options matrix and decision

#### 1.1 Summary table

| Option                              | Description                                          | When to choose                                                    | **G7 decision**      |
| ----------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------- | -------------------- |
| **B0 — Local Postgres**             | Docker Postgres locally; Supabase for staging/prod   | Default for dev teams wanting offline local DB                    | **Adopt (dev)**      |
| **B1 — Supabase Postgres (remote)** | Staging/prod use Supabase pooler `DATABASE_URL`      | Hosted DB without local Docker; solo devs may use B1 for all envs | **Adopt (stg/prod)** |
| **B2 — Supabase Auth**              | OAuth/magic links via Supabase; app schema unchanged | When delegating auth to Supabase                                  | **Defer**            |
| **B3 — RLS on `owner_id`**          | Postgres RLS policies; optional B2 (Supabase Auth)   | Strongest tenant isolation at DB layer                            | **Defer**            |

#### 1.2 B0 — Local Postgres (development)

|                 |                                                                                                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | `docker/database/docker-compose.yml` runs Postgres 15; `DATABASE_URL` points at `localhost`. Staging/prod use Supabase (B1).                                          |
| **Pros**        | Offline dev; fast Alembic iteration; matches CI [`migration-check.yml`](../../.github/workflows/migration-check.yml); no cloud dependency for unit/integration tests. |
| **Cons**        | Developers must run Docker; schema drift if local and remote migrations diverge; two connection configs to maintain.                                                  |
| **Code impact** | `Settings.DATABASE_URL` → `SQLDatabaseConnector.establish()` only; no Supabase SDK required.                                                                          |

#### 1.3 B1 — Supabase Postgres (staging / production)

|                 |                                                                                                                                                |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | All remote environments use Supabase project connection string (pooler). Optional: solo developers may use B1 for dev too if they skip Docker. |
| **Pros**        | Single ops model; managed backups, dashboard, branching; aligns with NFR-07 FK validation on real Supabase.                                    |
| **Cons**        | Requires network; pooler mode constraints (see §2); secrets in Supabase dashboard / deployment env.                                            |
| **Code impact** | Same `DATABASE_URL` wiring as B0; document pooler URL format and engine options.                                                               |

#### 1.4 B2 — Supabase Auth (deferred)

|                 |                                                                                                                                                                            |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | Replace or bridge local JWT issuance with Supabase Auth (`auth.users`); FastAPI validates Supabase JWT or exchanges session.                                               |
| **Pros**        | OAuth, magic links, MFA, hosted session management; less custom auth code long-term.                                                                                       |
| **Cons**        | Rewrites FR-10/FR-11 mid-refactor; requires `auth.users.id` ↔ `papita_transactions.users.id` sync; PR #27 `Users` + `AuthSecurityManager` investment abandoned or bridged. |
| **Defer until** | `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` (G5) explicitly evaluates Supabase Auth vs local JWT.                                                             |

#### 1.5 B3 — RLS on `owner_id` (deferred)

|                 |                                                                                                                                                                                                                                                            |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mechanism**   | PostgreSQL RLS policies on tenant-scoped tables; API sets `app.user_id` per request from JWT `sub` (works with **B0/B1 local JWT** — Supabase Auth/B2 not required).                                                                                       |
| **Pros**        | Defense-in-depth; DB blocks cross-tenant reads even if repository filter is omitted.                                                                                                                                                                       |
| **Cons**        | Doubles isolation logic (app layer + DB); global `categories` seeds (`owner_id NULL`) need special policies; service-role bypass for admin/migrations; test matrix doubles.                                                                                |
| **Defer until** | App-layer tenancy proven (v3 + G5); implement in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) / v4.7 per [`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3). |

**Note:** B3 is **not blocked on B2**. If B2 (Supabase Auth) is adopted later, map its `sub` to `app.user_id` the same way as local JWT.

#### 1.6 Phased rollout (proposed for G7)

| Phase       | Environment         | Option         | Auth                                                                                                                |
| ----------- | ------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Now**     | Local dev, CI       | B0             | Local JWT (after G5 auth contract)                                                                                  |
| **Now**     | Staging, production | B1             | Local JWT                                                                                                           |
| **Post-G5** | Any                 | Re-evaluate B2 | Supabase Auth if chosen in auth contract                                                                            |
| **Post-v3** | Staging first       | B3             | RLS on `owner_id` tables ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)); compatible with B0/B1 JWT |

---

### 2. `DATABASE_URL` formats

SQLAlchemy driver in this repo: **`postgresql+psycopg2`** (see root README and Alembic config). `Settings` passes the URL string to `SQLDatabaseConnector.establish()`, which calls `sqlalchemy.create_engine()`.

#### 2.1 B0 — Local Docker Postgres

```bash
## modules/api/src/.env (API Settings) or exported for Alembic
DATABASE_URL="postgresql+psycopg2://papita:changeme@localhost:5432/papita_transactions"
```

Compose defaults: see `docker/database/docker-compose.yml`. Create `docker/database/.env` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` (or `DB_*` aliases).

**Alembic / migrations:** use a **direct** Postgres URL (not pooler). Local Docker satisfies this.

#### 2.2 B1 — Supabase pooler

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
## Pooler session mode
DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres"

## Direct connection (migrations, one-off admin)
DATABASE_URL="postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres"
```

#### 2.3 SQLAlchemy engine guidance

| Concern             | Transaction pooler (6543)                                                                                                                                   | Session / direct (5432)                     |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Connection pooling  | Modest `pool_size=DATABASE_POOL_SIZE` (default 5) + `max_overflow=0` on pooler URLs (PPT-039 [#49](https://github.com/Elmorralito/save-ma-money/issues/49)) | Standard SQLAlchemy pool                    |
| Prepared statements | **psycopg2** (current driver): modest QueuePool is the default; switch to `NullPool` if PgBouncer timeouts appear; `prepare_threshold` is **psycopg3 only** | Default OK                                  |
| Health checks       | `pool_pre_ping=True` on API engine (wired in Settings → `establish`, PPT-039)                                                                               | Same                                        |
| Migrations          | **Avoid** transaction pooler — use direct URL or session mode                                                                                               | **Required** for `./bin/alembic.sh upgrade` |
| SSL                 | Supabase requires TLS in production                                                                                                                         | Add `?sslmode=require` if not implicit      |

**Implementation note (PPT-039):** API `Settings` passes `pool_pre_ping=True`, `pool_size=DATABASE_POOL_SIZE`, and (on transaction-pooler URLs) `max_overflow=0` into `SQLDatabaseConnector.establish()`. Use `DATABASE_URL_MIGRATIONS` for Alembic-only direct connections while the API uses the transaction pooler. Checklist: [`docs/design/README.md` § Ops](../design/README.md#optional-b1-hosted-postgres-pooler).

---

### 3. Environment variables (NFR-05)

Template: [`environments/<name>/.env.example`](../../environments/README.md) — **copy to `environments/<name>/.env`** and set `PAPITA_ENV`. **Never commit real `.env` files.**

`papita_txnsapi.Settings` loads from `environments/$PAPITA_ENV/.env`. Alembic / Docker use the same file via `bin/alembic.sh --env` and `docker compose --env-file`.

#### 3.1 Variable reference

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

#### 3.2 Per-environment examples

| Environment     | `DATABASE_URL` source                | Other vars                                           |
| --------------- | ------------------------------------ | ---------------------------------------------------- |
| Local dev (B0)  | `localhost:5432` via Docker          | `JWT_SECRET_KEY` (dev-only secret)                   |
| CI              | Ephemeral Postgres service container | Test `JWT_SECRET_KEY` from workflow env              |
| Staging (B1)    | Supabase transaction pooler `:6543`  | Production-grade `JWT_SECRET_KEY` in secrets manager |
| Production (B1) | Supabase transaction pooler `:6543`  | Same; rotate keys via deployment platform            |

---

### 4. FastAPI integration notes

FastAPI app (`main.py`, routers) is **not implemented yet** ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)). This section records the intended wiring against current code.

#### 4.1 Settings bootstrap

`Settings` (`modules/api/src/papita_txnsapi/config/settings.py`):

- Loads `.env` from `modules/api/src/.env`
- Validates `DATABASE_URL` via `SQLDatabaseConnector.establish(connection=value)` — engine is created at settings init
- Requires `JWT_SECRET_KEY` (no default — app fails fast without it)
- **DuckDB fallback:** if `DATABASE_URL` is missing or empty, Settings warns and calls `establish(connection=None)`, which still resolves to a legacy DuckDB path in `connector.py`. **Always set an explicit Postgres `DATABASE_URL`** in every environment until #25 removes the fallback.

#### 4.2 Session dependency (recommended pattern for #25)

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

#### 4.3 Auth wiring (B0/B1)

`AuthSecurityManager` (`modules/api/src/papita_txnsapi/core/security.py`):

- `generate_token(user_id)` — embeds `sub`, `exp`, `iat`, `type`
- `authenticate_and_get_token(username, password, verify_credentials)` — expects injectable verifier
- `decode_token(token)` — validates signature and expiry

**Gaps (Track E, not this issue):**

- `UsersService` has **no** `verify_credentials()` — must be added before `/auth/login`
- `PasswordManagerFactory` is **uninitialized** until `get_password_manager(keyword="argon2")` (or similar) runs at app startup

**JWT `sub` claim:** string form of `papita_transactions.users.id` (UUID). Today `UsersDTO` **deterministically** sets `id = uuid5(NAMESPACE_URL, sha256(username))` — auth contract (G5) must confirm or change this before login ships.

#### 4.4 Health checks

API spec (`modules/api/API_Endpoints.md.md`) defines:

| Endpoint            | Purpose             | Implementation sketch                                                 |
| ------------------- | ------------------- | --------------------------------------------------------------------- |
| `GET /health`       | Overall status + DB | `SQLDatabaseConnector.connected()` + `session.exec(text("SELECT 1"))` |
| `GET /health/ready` | K8s readiness       | DB reachable                                                          |
| `GET /health/live`  | K8s liveness        | Process up (no DB required)                                           |

Return `"database": "connected"` only when `SELECT 1` succeeds. On Supabase B1, transient pooler errors should map to 503 on `/health/ready`, not 500 on liveness.

#### 4.5 CORS

`Settings.ALLOWED_ORIGINS` defaults to `["*"]` — acceptable for local dev only.

| Environment     | Recommendation                                                                |
| --------------- | ----------------------------------------------------------------------------- |
| B0 local        | `["http://localhost:3000", "http://127.0.0.1:3000"]` or `*` for quick testing |
| B1 staging/prod | Explicit frontend origin(s); **never** `*` if `allow_credentials=True`        |
| B2/B3 (future)  | Include Supabase Auth redirect URLs if using browser OAuth                    |

Planned middleware (from API README scaffold): `CORSMiddleware` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

---

### 5. Auth implications matrix (FR-10, FR-11)

Input: Track E in [`PPT-031-simplify-requirements.md`](#part-i--ppt-031-simplify-requirements-28) §Track E, PR #27 `Users` table.

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

### 6. RLS policy outline (B3 — implementation in #34)

RLS is **deferred** (G7). v3 schema (proposed) uses **Strategy B** — denormalized `owner_id` on hot tables with app-layer enforcement ([#32](https://github.com/Elmorralito/save-ma-money/issues/32) §3.2). B3 adds **Strategy C** as defense-in-depth and works with **local JWT (B0/B1)** or Supabase Auth (B2).

#### 6.1 v3 tables — RLS candidates

| Table                                       | `owner_id` | Policy notes                                                      |
| ------------------------------------------- | ---------- | ----------------------------------------------------------------- |
| `papita_transactions.accounts`              | NOT NULL   | Standard tenant isolation                                         |
| `papita_transactions.transactions`          | NOT NULL   | Standard                                                          |
| `papita_transactions.transaction_templates` | NOT NULL   | Standard                                                          |
| `papita_transactions.account_financing`     | NOT NULL   | Standard                                                          |
| `papita_transactions.categories`            | NULLABLE   | Global seeds: `owner_id IS NULL OR owner_id = current_user`       |
| `papita_transactions.users`                 | N/A        | Policy: `id = current_user` for self-read; admin via service role |
| `*_account_details` (1:1 extensions)        | absent     | No direct RLS — access via `accounts` join or inherit FK policy   |

#### 6.2 Policy template

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

#### 6.3 Service contract (when B3 is adopted)

1. FastAPI auth dependency decodes JWT → `current_user_id`
2. Before repository calls: `session.connection().execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(current_user_id)})`
3. Keep `OwnedTableRepository` filters — RLS is **additive**, not a replacement ([`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3))
4. Migrations / backfill: use `SUPABASE_SERVICE_ROLE_KEY` or direct Postgres role that bypasses RLS
5. Alembic revision series: `V4-13` or dedicated RLS migration in [#34](https://github.com/Elmorralito/save-ma-money/issues/34)

#### 6.4 v4 extension tables (future)

When v4 ships, extend policies to: `budgets`, `budget_allocations`, `transaction_splits`, `counterparties`, `categorization_rules`, `account_reconciliations`, `reconciliation_items`, `transaction_attachments`, `import_batches`, `tags` — full list in [`ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a` §6](../design/ARCHITECTURE.md#6-rls-policy-outline-v47--b3).

---

### Deliverables

- [x] Decision record: chosen B0–B3 with pros/cons
- [x] `DATABASE_URL` format for Supabase pooler (transaction vs session mode)
- [x] Env var documentation: `DATABASE_URL`, `JWT_SECRET_KEY`, optional `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (NFR-05)
- [x] FastAPI integration notes: session DI via `SQLDatabaseConnector`, health checks, CORS
- [x] Auth implications for B2/B3 tied to FR-10, FR-11 (Track E in #28)
- [x] RLS policy outline for B3 (Alembic SQL migrations in #34)
- [x] `.env.example` template (do not commit secrets)

### Open items (explicitly deferred)

| Item                              | Gate / issue                                                                                                                  | Notes                                                                                                                                   |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| G1 v3 schema freeze               | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) / [#32](https://github.com/Elmorralito/save-ma-money/issues/32) | Tenancy in §1.6 / v3 §3.2; RLS in §6 — **proposed**, not maintainer-approved                                                            |
| G5 auth contract                  | Track E                                                                                                                       | `ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` — blocks `/auth/*` in #25                                                      |
| G7 maintainer sign-off            | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)                                                                 | Confirm B0+B1 on #28; [#31](https://github.com/Elmorralito/save-ma-money/issues/31) deliverables complete — issue may close on PR merge |
| B2 Supabase Auth                  | G7 phase 2                                                                                                                    | Re-evaluate after G5                                                                                                                    |
| B3 RLS implementation             | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)                                                                 | SQL migrations only; no policies in this PR                                                                                             |
| `UsersService.verify_credentials` | #25 / G5                                                                                                                      | Code change out of scope                                                                                                                |
| `DATABASE_URL_MIGRATIONS` split   | PPT-039 [#49](https://github.com/Elmorralito/save-ma-money/issues/49)                                                         | Direct URL for Alembic vs pooler for API; see [`docs/design/README.md` § Ops](../design/README.md#optional-b1-hosted-postgres-pooler)   |
| FastAPI `main.py` + routers       | [#25](https://github.com/Elmorralito/save-ma-money/issues/25)                                                                 | Implementation blocked on G1                                                                                                            |

### References

- `modules/api/src/papita_txnsapi/config/settings.py`
- `modules/api/src/papita_txnsapi/core/security.py`
- `modules/model/src/papita_txnsmodel/database/connector.py`
- `modules/model/src/papita_txnsmodel/services/users.py`
- `docker/database/docker-compose.yml`
- Migrations: [#34](https://github.com/Elmorralito/save-ma-money/issues/34)
- Env template: [`.env.example`](../../.env.example)

---

## Part III — PPT-032 API epic (#42)

> GitHub epic body draft for FastAPI MVP. [#42](https://github.com/Elmorralito/save-ma-money/issues/42).

### Summary

**Program:** PPT-032 · **Parent:** #28 (PPT-031)

Implement the **MVP REST API** in `modules/api` (`papita-txnsapi`) using **FastAPI**, backed by the **v3 `papita_txnsmodel`** layer and **PostgreSQL** (Docker local / any hosted Postgres). **Supabase is used for Auth only** (PPT-039 / #49) — not as a required database host.

Design tracks A–E are complete under PPT-031 (#30, #31, #32, #33, #34). **PPT-041** (#51) and all API children **#43–#50 are closed** — epic remains open for formal close-out only.

> **Note:** #25 (PPT-030) was a placeholder and is **not** this tracker.
>
> **2026-07-13 pivot:** Epic no longer requires Supabase PostgreSQL (pooler) for close-out. Prior B1 pooler work remains optional ops. See [#49](https://github.com/Elmorralito/save-ma-money/issues/49) reissue and [G7 Auth-first supersede](#g7-supersede-2026-07-13--auth-first).

---

### Platform integration model

| Layer           | Local / CI                     | Staging / prod                            | Deferred                   |
| --------------- | ------------------------------ | ----------------------------------------- | -------------------------- |
| **Database**    | Docker Postgres 15             | Any Postgres URL (Supabase PG _optional_) | —                          |
| **API runtime** | FastAPI + Uvicorn              | Same app                                  | —                          |
| **Auth (MVP)**  | Supabase Auth (JWT verify)     | Supabase Auth                             | Extra OAuth providers      |
| **Migrations**  | `./bin/alembic.sh --env local` | Direct Postgres URL                       | RLS policy migrations (B3) |

**Rule:** Domain sub-issues validate on Docker Postgres (B0). Staging Auth must validate **Supabase Auth JWTs** (PPT-039). Supabase-hosted Postgres is **not** an epic gate.

---

### Canonical documentation

| Document                                                                                        | Role                                                                |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [`modules/api/README.md`](../../modules/api/README.md)                                          | **Canonical** API reference (status, integration, endpoint catalog) |
| [`ARCHITECTURE.md` Part IV](../design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) | Endpoint → Service → DTO → SQLModel map                             |
| [`ARCHITECTURE.md` Part V](../design/ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43)    | PPT-033 coverage matrix                                             |
| [`ARCHITECTURE.md` Part VI](../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)   | Auth contract (Supabase Auth)                                       |
| [This README Part II](#part-ii--ppt-031-c-supabase--fastapi-decision-31)                        | B0/B1/B2/B3 + **G7 Auth-first supersede**                           |
| [This README Part IV](#part-iv--ppt-039-supabase-auth-reissue-49)                               | PPT-039 Auth reissue                                                |
| [`environments/README.md`](../../environments/README.md)                                        | `PAPITA_ENV` / Auth / DB templates                                  |
| [`docs/design/README.md`](../design/README.md)                                                  | PPT-031 program index                                               |

> Legacy filenames `API_Endpoints.md.md` / `API_Documentation.md.md` / standalone mapping files were merged into `modules/api/README.md` + `docs/design/ARCHITECTURE.md`.

---

### Prerequisites (gates)

- [x] **G1** — v3 schema freeze (PPT-031-B / #32) — implemented in model + migrations
- [x] **G3** — API ↔ model mapping (PPT-031-D / #33) — Part IV + API README
- [x] **G5** — Auth contract — Supabase Auth via PPT-039 / Part VI
- [x] **G7** — **Superseded 2026-07-13:** Auth = Supabase; hosted Postgres optional ([supersede](#g7-supersede-2026-07-13--auth-first))
- [x] **PPT-031-E** — v3 migration (#34)
- [x] **PPT-041** — v3 model hardening (#51)

---

### MVP scope (32 endpoints)

Per [`ARCHITECTURE.md` Part IV](../design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) §6 / [`modules/api/README.md`](../../modules/api/README.md):

- Health (3+), auth register/login (2) — Supabase Auth JWTs; API pass-through optional
- Accounts (6), categories (5)
- Transactions (6), movements alias (6)
- Reports (4)

**Deferred (501):** `/budgets/*`, `/transactions/{id}/split`, `/reports/budget-performance`.
**Auth refresh/logout:** implemented when `AUTH_PROVIDER=supabase`; **501** in local HS256 mode.

---

### Architecture

```
HTTP → papita_txnsapi/routers → schemas (I/O only) → papita_txnsmodel/services → repositories → PostgreSQL
Auth: Supabase access JWT → get_current_owner(sub) → owner_id
```

- Business rules stay in model DTOs/services — **no duplication in API layer**
- Tenant scope: JWT `sub` → `UsersService.get_owner()` → `owner_id` on all protected calls
- Enum convention: API JSON lowercase slugs ↔ DB uppercase enums

---

### Dependency graph

```mermaid
flowchart TD
    subgraph p0 [Phase 0 Design — PPT-031 DONE]
        G1["PPT-031-B #32"]
        G3["PPT-031-D #33"]
        G5[G5 auth contract]
        G7d["PPT-031-C #31"]
    end

    subgraph p1 [Phase 1 Migration — PPT-031-E]
        M1["#34 Alembic v3 seed"]
        M2[Docker Postgres validate]
    end

    subgraph p1b [Phase 1b Model hardening — PPT-041]
        H1["#51 Service layer G1 G3 G5"]
        H2[Balance mat. views]
        H3[Live-DB tenant tests]
        H4[Handler regression]
    end

    subgraph p2 [Phase 2 FastAPI MVP — PPT-032]
        F0["PPT-033 #43 Doc validation"]
        F1["PPT-034 #45 Scaffold + health"]
        F2["PPT-035 #44 Auth + tenant"]
        F3["PPT-036 #46 Accounts + categories"]
        F4["PPT-037 #47 Txns + movements"]
        F5["PPT-038 #48 Reports"]
        F6["PPT-039 #49 Supabase Auth"]
        F7["PPT-040 #50 Tests + CI"]
    end

    subgraph p3 [Phase 3 Hardening]
        CI[CI gates]
        OA[OpenAPI runtime truth]
    end

    subgraph p4 [Phase 4 Post-MVP]
        B1opt[Optional Supabase Postgres host]
        B3[RLS B3]
        V4[v4 API extensions]
    end

    p0 --> p1
    M1 --> M2 --> p1b
    H1 --> H2 --> H3 --> H4
    H4 --> F0 --> F1
    F1 --> F2 --> F3 --> F4 --> F5
    F1 --> F6
    F2 --> F7
    F5 --> F7
    F6 --> F7
    F7 --> p3 --> p4
```

#### Implementation order (all delivered)

| Step | PPT         | Issue                        | Status |
| ---- | ----------- | ---------------------------- | ------ |
| —    | PPT-031-E   | #34 Migration                | Closed |
| —    | **PPT-041** | **#51 Model hardening**      | Closed |
| 0    | PPT-033     | #43 Doc validation           | Closed |
| 1    | PPT-034     | #45 App scaffold + health    | Closed |
| 2    | PPT-035     | #44 Auth + tenant module     | Closed |
| 3    | PPT-036     | #46 Accounts + categories    | Closed |
| 4    | PPT-037     | #47 Transactions + movements | Closed |
| 5    | PPT-038     | #48 Reports                  | Closed |
| 6    | PPT-039     | #49 Supabase Auth            | Closed |
| 7    | PPT-040     | #50 Tests + CI (Auth-first)  | Closed |

---

### Sub-issues

- [x] PPT-033 / #43 — Doc validation
- [x] PPT-034 / #45 — App scaffold + health
- [x] PPT-035 / #44 — Auth + tenant module
- [x] PPT-036 / #46 — Accounts + categories
- [x] PPT-037 / #47 — Transactions + movements
- [x] PPT-038 / #48 — Reports
- [x] PPT-039 / #49 — **Supabase Auth** (repurposed from pooler wiring)
- [x] PPT-040 / #50 — Tests + CI (B0; Auth-first)

**Prerequisite (PPT-031 under #28):** PPT-041 / #51 — v3 model hardening — **closed**

---

### Epic acceptance criteria

- [x] All 32 MVP endpoints match [`modules/api/README.md`](../../modules/api/README.md) (auth paths updated for Supabase Auth)
- [x] OpenAPI at `/api/openapi.json` generated from running app
- [x] Protected routes enforce tenant isolation via `owner_id`
- [x] Protected routes validate **Supabase Auth** access JWTs (`sub` → owner)
- [x] `/health/ready` returns DB status on Docker Postgres (B0)
- [x] `modules/api/tests/` with router integration tests in CI
- [x] Deferred routes return **501** if mounted (budgets, split, budget-performance; local refresh/logout)
- [x] ~~Validated on Supabase pooler~~ **Waived** — Supabase PG optional; Auth validated via PPT-039 (`make auth-smoke`)

> Maintainer action: confirm ACs above and **close [#42](https://github.com/Elmorralito/save-ma-money/issues/42)**.

### Out of scope

- **Requiring** Supabase Auth **and** Supabase-hosted Postgres as the same MVP deliverable
- Supabase Postgres pooler as epic gate (optional ops only)
- RLS policies (B3)
- Budgets, transaction splits (v4); local-mode refresh/logout without Redis
- DuckDB

---

**Parent program:** #28 (PPT-031) · **Prerequisites #34 + #51:** satisfied · **Children #43–#50:** closed

---

## Part IV — PPT-039 Supabase Auth reissue (#49)

> Auth-only pivot (pooler ACs waived). Closed. [#49](https://github.com/Elmorralito/save-ma-money/issues/49). (`_gh_body_PPT-039.md` was a duplicate draft and is not included.)

**GitHub:** [#49](https://github.com/Elmorralito/save-ma-money/issues/49) · **Epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) · **Program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28)

**Status:** Issue scope **repurposed 2026-07-13** — Supabase **Auth only**. Prior B1 Postgres pooler ACs for PPT-039 are **waived** (optional ops; not MVP).

**Impl status:** [#49](https://github.com/Elmorralito/save-ma-money/issues/49) **closed**. JWKS verify + provision + env templates + G5/Part VI landed; Auth smoke via `make auth-smoke`. Canonical operator docs: [`modules/api/README.md`](../../modules/api/README.md).

See also: [PPT-031-C supersede note](#g7-supersede-2026-07-13--auth-first).

---

**Parent program:** #28 (PPT-031) · **Parent epic:** #42 (PPT-032) · **PPT-039** · **Step:** 6 (Auth = Supabase)

### Summary

Replace local HS256 issuance (`AuthSecurityManager` + `JWT_SECRET_KEY`) with **Supabase Auth**. FastAPI validates Supabase JWTs and maps `sub` → `papita_transactions.users` / tenant `owner`. Database hosting remains **Docker Postgres (B0) or any Postgres URL** — **not** in scope for this issue.

**Supersedes prior #49 focus** (Supabase transaction pooler / B1 DB wiring). Landed pooler docs/engine/smoke are dispositioned below — do not redo as AC here.

### Depends on

- #44 (PPT-035) — auth + tenant module (exists; this issue rewires it)
- Soft: G5 auth-contract update noting Supabase Auth as MVP choice ✅ ([`ARCHITECTURE.md` Part VI](../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e))
- Soft: #89 for prod CORS/docs posture when Auth is public

### Blocks

- #50 (PPT-040) — CI secrets become Supabase Auth (`SUPABASE_URL` / JWKS + test project), not required pooler `DATABASE_URL`
- Cleaner epic #42 AC (Auth, not pooler DB)

### Platform rule (updated)

| Layer          | Local / CI                             | Staging / prod                                                           |
| -------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| **Database**   | Docker Postgres (or any PG URL)        | Same app; **any** hosted Postgres (Supabase PG _optional_, not required) |
| **Auth**       | Supabase Auth (project or local stack) | Supabase Auth                                                            |
| **Migrations** | `./bin/alembic.sh --env local`         | Direct PG URL — independent of Auth                                      |

### Disposition of prior B1 DB work (landed)

| Item                                                                                 | Disposition                                                      |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `environments/*` pooler templates, checklist, `pool_pre_ping` / `DATABASE_POOL_SIZE` | **Keep** as optional ops; not MVP AC                             |
| `test_supabase_b1_smoke.py` / `make b1-smoke`                                        | Pooler smoke **parked** optional; Auth smoke → `make auth-smoke` |
| Epic wording “validate on Supabase pooler”                                           | **Removed** via #42 edit                                         |

### Tasks / deliverables

#### Settings & env (`PAPITA_ENV`)

- [x] Document `SUPABASE_URL`, JWT verification mode (JWKS), `AUTH_PROVIDER` feature flag; local HS256 transitional
- [x] Update `environments/{local,staging,production}/.env.example` — Auth vars primary; pooler URLs secondary/commented

#### Runtime

- [x] `AuthSecurityManager.decode_token` validates Supabase JWT (`aud` / `iss` / `sub`) via JWKS
- [x] Register/login: client → Supabase Auth preferred; thin API pass-through when `SUPABASE_ANON_KEY` set
- [x] `get_current_owner`: `sub` → `ensure_from_auth_subject` (UUID alignment)
- [x] Keep `/health/live` DB-free; ready stays DB probe (unchanged)

#### Tests & docs

- [x] JWKS/mock token fixtures (`test_auth_supabase.py`); local HS256 suite retained for `AUTH_PROVIDER=local`
- [x] Auth smoke: `make auth-smoke` / `test_auth_smoke.py` (opt-in) → `/auth/me` + accounts
- [x] API README + auth contract Part VI + Strata; brief G7 supersede pointer

### Out of scope

- Requiring Supabase **Postgres** pooler for MVP
- RLS (B3), Redis, full PPT-044 pack
- OAuth provider matrix beyond email/password (follow-on)

### Acceptance criteria

- [x] Title/semantic `feat/PPT-039`; epic #42 no longer requires Supabase-hosted DB
- [x] Protected routes accept Supabase access JWT; local mint off when `AUTH_PROVIDER=supabase`
- [x] Tenant isolation still `owner_id` via `sub` mapping
- [x] Env templates document Auth secrets (values never in git)
- [x] Handoff to #50: `SUPABASE_URL` (+ JWKS); smoke entrypoint `make auth-smoke`
- [x] Prior pooler ACs explicitly waived / parked ops

### References

- PPT-031-C §1.4 B2 (pulled into MVP via this reissue)
- `modules/api/.../security.py`, `routers/v1/auth.py`, `dependencies/auth.py`
- Epic #42 · CI #50 · brief G7 supersede on #28

### Handoff to PPT-040 (#50)

| Name                         | Role                                                            |
| ---------------------------- | --------------------------------------------------------------- |
| `SUPABASE_URL`               | Project URL for JWKS / Auth API                                 |
| (optional) Supabase anon key | Client-side Auth / API pass-through                             |
| (optional) service role      | Server-only provisioning — never expose to clients              |
| `DATABASE_URL`               | Any Postgres (Docker or hosted) — **not** tied to Supabase Auth |

**Smoke entrypoint:** `make auth-smoke` — Auth JWT → `GET /api/v1/auth/me` (+ `/api/v1/accounts`). Pooler DB smoke remains optional (`make b1-smoke`).

---

## Part V — PPT-043 Redis integration (#83)

> Post-MVP Redis brief. [#83](https://github.com/Elmorralito/save-ma-money/issues/83).

**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-043** · **Step:** Post-MVP infrastructure

### Summary

Introduce **Redis as shared infrastructure** for `papita-txnsapi` after the FastAPI MVP epic closes. Redis replaces or extends current **single-instance, in-memory** patterns so the API can scale horizontally across replicas without losing rate-limit counters, cache coherence, or session/token state.

Today the API uses `InMemoryRateLimiter` (`modules/api/src/papita_txnsapi/core/rate_limit.py`) for auth endpoint throttling — effective on B0 single-process deployments only. The auth contract defers `/auth/logout` token denylist and refresh-token storage to a future Redis-backed store ([`ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` §6](../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)). This issue delivers the Redis foundation and P1 capabilities; worker fleets and real-time product features remain follow-on work.

### Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) — **all sub-issues closed** (#43–#50)
- [#50](https://github.com/Elmorralito/save-ma-money/issues/50) (PPT-040) — CI dual-target harness (recommended for Redis integration tests)

### Blocks

- Horizontal API scaling (multiple Uvicorn replicas / containers)
- Server-side `/auth/logout` JWT denylist (FR-11 follow-on)
- Tiered API rate limits per [`modules/api/README.md` Rate Limiting](../../modules/api/README.md)
- Background worker layer (report exports, MV refresh queues)
- Live notifications / pub-sub product features

### Platform rule (B0 + B1)

Redis is **additive** — PostgreSQL remains the source of truth.

| Layer        | B0 (local)                           | B1 (staging / prod)                 |
| ------------ | ------------------------------------ | ----------------------------------- |
| **Database** | Docker Postgres 15                   | Supabase transaction pooler `:6543` |
| **Redis**    | Docker Compose Redis 7 (new service) | Managed Redis URL (`REDIS_URL`)     |
| **API**      | FastAPI + Uvicorn                    | Same app, B1 env vars               |

Validate API behavior on **both** B0 and B1 PostgreSQL targets before closing. Redis must be optional in local dev (in-memory fallback when `REDIS_URL` unset).

### Cache-aside pattern

```
[ Client ] → [ API Server ] → [ Redis ]     (hit: fast return)
                    ↓ miss
            [ PostgreSQL B0/B1 ]
```

All cache keys **must** include `owner_id` from JWT `sub` → `TenantContext` for tenant isolation.

### Redis capabilities (phased)

| Capability                    | Purpose                                             | Current gap                               | Phase           |
| ----------------------------- | --------------------------------------------------- | ----------------------------------------- | --------------- |
| **Query caching**             | Cache hot GET paths (accounts, categories, reports) | Every request hits PostgreSQL             | **P1**          |
| **Distributed rate limiting** | Shared counters across API replicas                 | `InMemoryRateLimiter` is process-local    | **P1**          |
| **Session / token store**     | JWT denylist, refresh-token prep                    | `/auth/logout` returns 501; no revocation | **P2**          |
| **Task queue (broker)**       | Background jobs (exports, MV refresh)               | No worker layer                           | **P3 scaffold** |
| **Pub/Sub**                   | Cache invalidation broadcasts, live notifications   | Not implemented                           | **P3 scaffold** |

### Tasks / deliverables

#### Infra

- [ ] Add Redis 7 service to `docker/database/docker-compose.yml` (or sibling compose file) with healthcheck
- [ ] Document `REDIS_URL`, `REDIS_ENABLED`, TTL defaults in `modules/api/src/.env.example` and root `.env.example`
- [ ] B1 runbook note for managed Redis (Upstash, ElastiCache, or Supabase-compatible provider) — placeholders only, no secrets

#### API core (`modules/api/src/papita_txnsapi/`)

- [ ] `core/redis.py` — connection pool (redis-py or aioredis), lifespan init/teardown, `ping()` helper
- [ ] Extend `/health/ready` to include Redis status when `REDIS_ENABLED=true` (503 if required and unreachable)
- [ ] `core/cache.py` — cache-aside decorator/dependency; key builder: `{owner_id}:{route}:{hash(params)}`
- [ ] `core/rate_limit.py` — `RedisRateLimiter` implementing same `RateLimitResult` interface as `InMemoryRateLimiter`; feature flag `REDIS_RATE_LIMIT_ENABLED`; retain in-memory fallback
- [ ] `core/session_store.py` — JWT denylist SET with TTL aligned to `JWT_EXPIRATION_TIME_SECONDS` (interface only; wire `/auth/logout` in follow-on)
- [ ] `core/broker.py` — queue/pub-sub interface + settings scaffold (no full worker fleet)

#### Settings

- [ ] `config/settings.py` — `REDIS_URL`, `REDIS_ENABLED`, `REDIS_DEFAULT_TTL_SECONDS`, `REDIS_RATE_LIMIT_ENABLED`, pool size

#### Tests (`modules/api/tests/`)

- [ ] Integration tests with fakeredis or Docker Redis (cache hit/miss, distributed rate limit across two client processes)
- [ ] `/health/ready` returns Redis component when enabled
- [ ] Existing B0 API test suite still passes with `REDIS_ENABLED=false`

#### Docs / memory

- [ ] Update `modules/api/README.md` — Redis section, env table, cache pattern diagram
- [ ] `.strata/docs/ARCHITECTURE.md` + `.strata/memory/project_state.md` if architecture changes (Strata strict mode)

### API integration

- [ ] B0 acceptance — Docker Postgres + Docker Redis, cache + rate limit proven
- [ ] B1 acceptance — Supabase pooler `DATABASE_URL` + managed `REDIS_URL` smoke test documented
- [ ] Env vars / docs updated (`.env.example`, README)

### Requirements traceability

| ID           | Scope                                                         |
| ------------ | ------------------------------------------------------------- |
| FR-11        | JWT denylist prep for future `/auth/logout`                   |
| NFR-04       | Rate limiting — distributed counters, `X-RateLimit-*` headers |
| NFR-05       | Env-driven config (`REDIS_URL`, feature flags)                |
| Epic #42 gap | Horizontal scaling beyond single-instance in-memory state     |

### Dependency graph

```mermaid
flowchart TD
    EPIC["PPT-032 #42 FastAPI MVP"]
    P040["PPT-040 #50 Tests + CI"]
    P043["PPT-043 Redis integration"]
    LOGOUT["FR-11 /auth/logout denylist"]
    WORKERS["Background workers"]
    LIVE["Pub/Sub live features"]

    EPIC --> P043
    P040 --> P043
    P043 --> LOGOUT
    P043 --> WORKERS
    P043 --> LIVE
```

### Out of scope

- Expanding MVP endpoint surface inside #42
- Supabase Auth (B2), RLS policies (B3)
- Full Celery/RQ/ARQ worker deployment
- Chat, push notifications, or other real-time product features
- Replacing PostgreSQL as source of truth
- Redis Cluster / Sentinel production hardening (document as follow-on)

### Acceptance criteria

- [ ] `REDIS_ENABLED=true` with valid `REDIS_URL` — `/health/ready` reports Redis connected
- [ ] Cache-aside on at least one protected GET route reduces duplicate DB queries (test assertion)
- [ ] `RedisRateLimiter` enforces limits consistently across two API processes (integration test)
- [ ] `REDIS_ENABLED=false` — API runs with in-memory fallback; no regression in existing tests
- [ ] All cache and rate-limit keys are tenant-scoped (`owner_id` prefix)
- [ ] B0 + B1 PostgreSQL API validation still passes per PPT-040 harness
- [ ] No secrets committed; `.env.example` placeholders only

### File change inventory

Review of all API files that need to be created or modified for PPT-043. Current tree: **25 source files**, **11 test files**, **no Redis code yet**.

#### Current baseline

| Area          | Today                                                                                  |
| ------------- | -------------------------------------------------------------------------------------- |
| Rate limiting | `InMemoryRateLimiter` — process-local, IP-scoped on `/auth/login` and `/auth/register` |
| Sessions      | Stateless JWT only; `/auth/logout` returns 501                                         |
| Health        | DB-only probes on `/health`, `/health/ready`                                           |
| Lifespan      | Password manager bootstrap only (`main.py`)                                            |
| Routers       | `health`, `auth`, deferred `budgets` — no accounts/categories/transactions/reports yet |

Redis is referenced only in comments (`config/settings.py:50`) and design docs — no client, cache, or denylist code exists.

#### Phase map

```mermaid
flowchart TD
    P1["P1 — Ship first"]
    P2["P2 — Session store"]
    P3["P3 — Scaffold only"]

    P1 --> S[settings + main lifespan]
    P1 --> R[core/redis + rate_limit]
    P1 --> H[health probes]
    P1 --> C[core/cache + tests]

    P2 --> SS[session_store + auth denylist]
    P2 --> LOGOUT[routers/v1/auth logout]

    P3 --> B[core/broker interface]
```

#### New files (create)

| File                                                   | Phase | Purpose                                                      |
| ------------------------------------------------------ | ----- | ------------------------------------------------------------ |
| `modules/api/src/papita_txnsapi/core/redis.py`         | P1    | Async connection pool, `ping()`, init/teardown helpers       |
| `modules/api/src/papita_txnsapi/core/redis_health.py`  | P1    | Redis readiness probe (or fold into `redis.py`)              |
| `modules/api/src/papita_txnsapi/core/cache.py`         | P1    | Cache-aside helper; keys `{owner_id}:{route}:{hash(params)}` |
| `modules/api/src/papita_txnsapi/dependencies/redis.py` | P1    | FastAPI DI: `get_redis_client`, no-op when disabled          |
| `modules/api/src/papita_txnsapi/dependencies/cache.py` | P1    | Cache dependency for protected GET routes                    |
| `modules/api/src/papita_txnsapi/core/session_store.py` | P2    | JWT denylist SET with TTL = `JWT_EXPIRATION_TIME_SECONDS`    |
| `modules/api/src/papita_txnsapi/core/broker.py`        | P3    | Queue/pub-sub interface scaffold only                        |
| `modules/api/tests/test_redis_health.py`               | P1    | Ready probe with Redis on/off                                |
| `modules/api/tests/test_redis_cache.py`                | P1    | Hit/miss, tenant key isolation                               |
| `modules/api/tests/test_redis_rate_limit.py`           | P1    | Distributed limiter across processes                         |
| `modules/api/tests/test_session_store.py`              | P2    | Denylist unit tests                                          |

#### Existing source files (modify)

##### P1 — Core wiring

| File                                                        | Change                                                                                                                                                 |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `modules/api/src/papita_txnsapi/config/settings.py`         | Add `REDIS_URL`, `REDIS_ENABLED`, `REDIS_DEFAULT_TTL_SECONDS`, `REDIS_RATE_LIMIT_ENABLED`, `REDIS_MAX_CONNECTIONS`; validator when enabled without URL |
| `modules/api/src/papita_txnsapi/main.py`                    | Extend `lifespan`: init Redis pool → `app.state.redis`, close on shutdown                                                                              |
| `modules/api/src/papita_txnsapi/core/rate_limit.py`         | Add `RedisRateLimiter` (same `RateLimitResult`); factory picks Redis vs in-memory                                                                      |
| `modules/api/src/papita_txnsapi/dependencies/rate_limit.py` | Use settings-aware factory; keep IP-scoped auth keys (`auth-login:{ip}`)                                                                               |
| `modules/api/src/papita_txnsapi/schemas/health.py`          | Add `redis: str` to `HealthResponse`; optionally `components` on `ReadinessResponse` (breaking probe schema)                                           |
| `modules/api/src/papita_txnsapi/routers/v1/health.py`       | Redis probe when `REDIS_ENABLED=true`; `/health/ready` 503 if DB or required Redis down                                                                |
| `modules/api/src/papita_txnsapi/dependencies/__init__.py`   | Export new Redis/cache dependencies if package re-exports them                                                                                         |

##### P1 — First cache target

| File                                                      | Change                                                                      |
| --------------------------------------------------------- | --------------------------------------------------------------------------- |
| `modules/api/src/papita_txnsapi/routers/v1/auth.py`       | Cache-aside on `GET /me` — only live protected GET today                    |
| `modules/api/src/papita_txnsapi/dependencies/tenant.py`   | Cache key builder consumes `TenantContext.owner_id`                         |
| `modules/api/src/papita_txnsapi/dependencies/services.py` | Optional cached wrapper around `get_owner()` (router-layer cache preferred) |

##### P2 — Session / logout prep

| File                                                  | Change                                                                  |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| `modules/api/src/papita_txnsapi/dependencies/auth.py` | After JWT decode, check denylist via `session_store.is_revoked()` → 401 |
| `modules/api/src/papita_txnsapi/routers/v1/auth.py`   | Wire `POST /logout` to add token to denylist (enable real logout)       |

##### Unlikely to change (P1)

| File                                   | Reason                                         |
| -------------------------------------- | ---------------------------------------------- |
| `core/security.py`                     | Encode/decode unchanged; denylist is external  |
| `core/db_health.py`                    | Postgres-only; Redis gets its own probe        |
| `core/handlers.py`                     | Exception handlers unchanged                   |
| `middleware/request_logging.py`        | No Redis coupling                              |
| `routers/v1/budgets.py`                | Deferred 501                                   |
| `schemas/auth.py`, `schemas/common.py` | No Redis fields unless logout response changes |
| `dependencies/pagination.py`           | Unrelated                                      |

#### Test files (modify)

| File                                       | Change                                                                   |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| `modules/api/tests/conftest.py`            | Default `REDIS_ENABLED=false`; `fakeredis` / Docker Redis fixtures       |
| `modules/api/tests/test_health.py`         | Redis in `/health` and `/health/ready`; 503 when Redis required and down |
| `modules/api/tests/test_auth_hardening.py` | Redis rate-limit path; keep in-memory fallback tests                     |
| `modules/api/tests/test_auth_protected.py` | Denylist rejection once P2 wired                                         |
| `modules/api/tests/auth_helpers.py`        | Optional helpers for Redis-enabled clients                               |

**Constraint:** All 11 existing test files must pass with `REDIS_ENABLED=false` — no Redis required for default CI.

#### Packaging and config

| File                           | Change                                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------ |
| `modules/api/pyproject.toml`   | Add `redis>=5` (`redis.asyncio`); dev/test: `fakeredis`                                          |
| `modules/api/src/.env.example` | `REDIS_URL`, `REDIS_ENABLED`, `REDIS_DEFAULT_TTL_SECONDS`, `REDIS_RATE_LIMIT_ENABLED`, pool size |
| `.env.example` (root)          | Parity with API template                                                                         |
| `docker/api/.env.example`      | Redis vars for full stack                                                                        |

#### Docker (B0 support for API)

| File                                 | Change                                                                                         |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `docker/database/docker-compose.yml` | Add Redis 7 + healthcheck on `papita-local-net`                                                |
| `docker/docker-compose.yml`          | Redis service; `REDIS_URL=redis://redis:6379/0` on `api`; `depends_on: redis: service_healthy` |

`docker/api/Dockerfile` — no change strictly required (`redis` is a pip dep).

#### Docs and memory

| File                              | Change                                                                |
| --------------------------------- | --------------------------------------------------------------------- |
| `modules/api/README.md`           | Redis section, env table, cache-aside diagram; update Rate Limiting   |
| `docs/issues/README.md` Part V    | Check off deliverables as implemented                                 |
| `.strata/docs/ARCHITECTURE.md`    | Redis in architecture (Strata strict mode)                            |
| `.strata/memory/project_state.md` | Track PPT-043 progress                                                |
| `.github/CI.md` / workflows       | Optional: Redis service container for integration tests (#50 harness) |

#### Future routers (post–#42 sub-issues)

When PPT-036–038 land, apply cache-aside on hot GETs:

| Future file                  | Cache candidates                          |
| ---------------------------- | ----------------------------------------- |
| `routers/v1/accounts.py`     | `GET /accounts`, `GET /accounts/{id}`     |
| `routers/v1/categories.py`   | `GET /categories`                         |
| `routers/v1/transactions.py` | `GET /transactions` (shorter TTL)         |
| `routers/v1/movements.py`    | TRANSFER alias reads                      |
| `routers/v1/reports/*.py`    | Report aggregations (highest cache value) |

`routers/v1/__init__.py` grows as routers are added — no Redis change to the aggregator itself.

#### Recommended implementation order

| Step | Files                                                                  | Risk                                 |
| ---- | ---------------------------------------------------------------------- | ------------------------------------ |
| 1    | `pyproject.toml`, `settings.py`, `.env.example`                        | Low — config only                    |
| 2    | `core/redis.py`, `main.py` lifespan                                    | Medium — connection lifecycle        |
| 3    | `core/rate_limit.py`, `dependencies/rate_limit.py`                     | Medium — preserve in-memory fallback |
| 4    | `schemas/health.py`, `routers/v1/health.py`, `test_health.py`          | Medium — probe contract change       |
| 5    | `core/cache.py`, `dependencies/cache.py`, `routers/v1/auth.py` (`/me`) | Medium — tenant key isolation        |
| 6    | New Redis test files + `conftest.py` fixtures                          | Medium                               |
| 7    | Docker compose files                                                   | Low                                  |
| 8    | P2: `session_store.py`, `dependencies/auth.py`, logout                 | Higher — auth behavior change        |
| 9    | P3: `core/broker.py` scaffold                                          | Low                                  |

#### Design constraints

1. **Fallback is mandatory** — `REDIS_ENABLED=false` must keep today's behavior; all existing tests depend on it.
2. **Tenant isolation** — every cache/rate-limit key for protected routes must prefix `owner_id`.
3. **Auth vs API rate limits** — auth stays IP-scoped; tiered API limits (README spec) are tenant/route-scoped and need Redis.
4. **Business logic stays in model** — Redis wiring only in `papita_txnsapi`, not `papita_txnsmodel`.
5. **Blocked by #42** — only `/auth/me` exists today for cache demo until accounts/reports routers ship.

**Total touch surface:** ~11 new files, ~15 modified files, ~4 Docker/config files, ~4 doc files — **~34 files** for full PPT-043 scope (P1–P3).

### References

- [PPT-032 epic #42](https://github.com/Elmorralito/save-ma-money/issues/42)
- [`docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e) — §6 logout denylist deferral
- [`modules/api/src/papita_txnsapi/core/rate_limit.py`](modules/api/src/papita_txnsapi/core/rate_limit.py) — current in-memory limiter
- [`modules/api/src/papita_txnsapi/routers/v1/health.py`](modules/api/src/papita_txnsapi/routers/v1/health.py) — readiness probe extension point
- [`docs/issues/PPT-031-C-supabase-decision-brief.md`](#part-ii--ppt-031-c-supabase--fastapi-decision-31) — B0/B1 platform model

---

**Blocked by:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032 epic — close when all sub-issues #43–#50 are done)

---

## Part VI — PPT-045 uvicorn process packaging (#93)

> Post-MVP ops packaging brief. Closed ([#93](https://github.com/Elmorralito/save-ma-money/issues/93), [PR #103](https://github.com/Elmorralito/save-ma-money/pull/103)).
> Technical packaging: [`ARCHITECTURE.md` Part IX](../design/ARCHITECTURE.md#part-ix--uvicorn-process-packaging-ppt-045-93) · operator run paths: [`modules/api/README.md`](../../modules/api/README.md).

**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-045** · **Step:** Post-MVP ops packaging

### Summary

Standardize how `papita_txnsapi` is **launched under uvicorn** for B0 Compose. Uvicorn runs **inside the API Docker image** (not as a host Poetry process). The gap closed here is **canonical Make entrypoints**, Settings/`HOST`/`PORT` vs Dockerfile bind clarity, worker guidance (especially vs Redis in-memory fallbacks), and runbook clarity so paths do not drift.

### Current state (inspected)

| Surface       | Today                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ASGI app      | `papita_txnsapi.main:app` + lifespan (password manager + optional Redis)                                                                               |
| Dep           | `uvicorn[standard]` in `modules/api/pyproject.toml`                                                                                                    |
| Compose image | `docker/api/Dockerfile` → `CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]` (literal; Settings `HOST`/`PORT` unused) |
| Make          | `api-up` (Compose `api` + deps) / `stack-up` / `redis-up` / `redis-smoke`                                                                              |
| Poetry        | No host serve script — runtime is Docker                                                                                                               |
| Settings      | `HOST`, `PORT`, `PAPITA_ENV`, DB/Auth/Redis already on `Settings`                                                                                      |

### Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) — parent epic
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-043) — Redis lifespan + `/health/redis` / ready contract (coordinate; do not regress)
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) (PPT-044) — related ops hardening (CORS/TrustedHost); keep scopes distinct

### Blocks

- Cleaner local DX for Auth smoke / Redis smoke against a consistently started API container
- Safer multi-replica notes before anyone enables `--workers` without Redis rate limits

### Platform rule (B0 + B1)

Validate process packaging on **B0 Docker Postgres** (and Compose Redis when enabled). Supabase remains **Auth-only** for MVP; do not require pooler DB for this issue. Staging/prod notes may document managed Redis + uvicorn flags without deploying K8s.

### Decisions to lock in this issue

1. **Canonical entrypoint** — `make api-up` → Compose `api` service (uvicorn in-container). `make stack-up` for full explicit stack.
2. **No host uvicorn for B0** — do not promote `poetry run uvicorn` as a day-to-day path; container `CMD` is SSOT.
3. **Compose `HOST`/`PORT`** — **documented exception**: literal `0.0.0.0:8000` (HEALTHCHECK / `EXPOSE` / `${API_PORT}:8000` publish). Settings `HOST`/`PORT` are optional metadata.
4. **Reload policy** — never `--reload` in Compose `CMD`.
5. **Workers** — B0 default **single worker**. Document: in-memory rate limiter is process-local; multi-worker requires `REDIS_RATE_LIMIT_ENABLED=true` (+ Redis denylist). Defer gunicorn+uvicorn-workers unless justified.
6. **Lifecycle** — uvicorn must run the FastAPI lifespan (Redis init/teardown).
7. **Health contract unchanged** — `/api/v1/health`, `/ready`, `/live`, `/redis` remain smoke targets (`make redis-smoke`).

### Tasks / deliverables

#### Ops / infra

- [x] Add Makefile target(s): `api-up` (Compose API container), document relationship to `stack-up` / `redis-up`
- [x] Document that runtime is Docker (no Poetry console serve script for B0)
- [x] Align Dockerfile/Compose CMD with `HOST`/`PORT` env (or document why flags stay literal `0.0.0.0:8000`)
- [x] Ensure Compose `api` service does not inject host `REDIS_URL=localhost` (already hardcoded `redis://redis:6379/0` — keep)

#### Docs

- [x] Update `modules/api/README.md` run sections: Docker-canonical paths
- [x] Update `environments/README.md` with Compose Redis URL + uvicorn-in-container notes
- [x] Short ops note on workers vs Redis rate-limit / denylist fail-closed

#### API package (minimal)

- [x] No `__main__.py` / host serve script — Make + Dockerfile `CMD` is enough

### API / infra integration

- [x] B0: `make api-up` → `/health/ready` true; optional `make redis-smoke`
- [x] B0: `make stack-up` → container healthcheck + ready
- [x] Env examples document `HOST`/`PORT` as metadata and `API_PORT` for publish
- [x] No secrets committed (`.env` stays gitignored)

### Requirements traceability

| ID      | Scope                                           |
| ------- | ----------------------------------------------- |
| NFR-04  | Operability — reproducible Compose start        |
| NFR-ops | Process packaging; readiness probes remain gate |
| PPT-043 | Lifespan Redis pool must start under uvicorn    |

### Out of scope

- Kubernetes / ECS / systemd unit files
- TLS termination / reverse proxy (Caddy, nginx, Traefik)
- gunicorn + uvicorn worker fleet (unless a short ADR justifies it)
- Changing REST routes or business logic in `papita_txnsmodel`
- Registrar, DuckDB, RLS (B3)
- Full PPT-044 security pack (CORS/TrustedHost/docs lockdown) — track on #89
- Host Poetry uvicorn as a supported B0 runtime

### Acceptance criteria

- [x] Documented canonical Compose command(s) (`make api-up` / `make stack-up`)
- [x] Dockerfile/Compose CMD aligned with Settings `HOST`/`PORT` **or** explicitly documented exception
- [x] Make convenience target(s) that start uvicorn **in Docker**
- [x] Worker guidance written (single-worker default; Redis required before multi-worker)
- [x] B0 smoke: API container up → ready → optional `make redis-smoke`
- [x] README (+ env README) updated; no secrets in git

### References

- `modules/api/src/papita_txnsapi/main.py` — `create_app`, lifespan, module `app`
- `docker/api/Dockerfile` — uvicorn `CMD` + live healthcheck
- `docker/docker-compose.yml` — `api` service env (Auth, DB, Redis)
- `Makefile` — `api-up`, `api-down`, `stack-up`, `redis-up`, `redis-smoke`
- `modules/api/README.md` — Compose run paths
- [`ARCHITECTURE.md` Part IX](../design/ARCHITECTURE.md#part-ix--uvicorn-process-packaging-ppt-045-93) — technical packaging decisions
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) PPT-043 Redis
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) PPT-044 hardening
- Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) PPT-032
