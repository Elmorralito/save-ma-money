# refactor(PPT-031): Simplify data model and align API design

> **GitHub issue:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
> **Canonical copy:** this file mirrors the #28 issue body in the repo.

## Document ↔ issue registry

| Document                                                                         | Issue                                                                 | Track            | Status           |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------- | ---------------- |
| [`PPT-031-simplify-requirements.md`](./PPT-031-simplify-requirements.md)         | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)         | Epic             | Active           |
| [`../design/PPT-031-v0-audit.md`](../design/PPT-031-v0-audit.md)                 | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)         | A — v0 audit     | Draft            |
| [`PPT-031-C-supabase-decision-brief.md`](./PPT-031-C-supabase-decision-brief.md) | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)         | B — Supabase     | Active           |
| `../design/PPT-031-v1-schema.md` _(planned)_                                     | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | A — v1–v3 schema | Pending          |
| `../design/PPT-031-api-model-mapping.md` _(planned)_                             | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)         | C — API spec     | Pending          |
| `../design/PPT-031-migration-runbook.md`                                         | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)         | D — Migration    | **Written (v0)** |
| `../design/PPT-031-auth-contract.md` _(planned)_                                 | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E | Auth             | Pending          |

**Related issues:** [#24](https://github.com/Elmorralito/save-ma-money/issues/24) tenancy · [#25](https://github.com/Elmorralito/save-ma-money/issues/25) API impl · [#17](https://github.com/Elmorralito/save-ma-money/issues/17) superseded · [#11](https://github.com/Elmorralito/save-ma-money/issues/11) versioning

---

## Executive summary

This issue is **phase 2 of PPT-031**. Phase 1 shipped in [#26](https://github.com/Elmorralito/save-ma-money/issues/26) via [PR #27](https://github.com/Elmorralito/save-ma-money/pull/27): a `users` table, password hashing utilities, and an `owner_id` column on nearly every entity.

Phase 2 does **not** add users again. It **simplifies** what phase 1 added, normalizes the schema toward **Third Normal Form (3NF)**, resolves open questions from [#24](https://github.com/Elmorralito/save-ma-money/issues/24) (per-user finance isolation), adopts **PostgreSQL via Supabase** as the sole database platform, documents **Supabase × FastAPI** integration, and realigns the API specification so [#25](https://github.com/Elmorralito/save-ma-money/issues/25) can implement endpoints against a stable domain model.

> **Platform decision (2026-07-02):** **DuckDB is out of scope.** All migrations, validation, and local dev target **PostgreSQL** (Docker Postgres locally; Supabase for hosted/staging). See [#34](https://github.com/Elmorralito/save-ma-money/issues/34). [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) is superseded.

**This issue is design-first.** Implementation PRs should follow sub-issues derived from the tracks below.

---

## Validation review (2026-07-02)

A second pass against the live codebase identified **gaps not fully covered** in the initial issue body. These are incorporated below as pain points **#7–#15**, **Tracks E–F**, and **FR-10–FR-17 / NFR-08–NFR-12**.

### Highest-risk gaps (must resolve before #25)

| Priority | Gap                                                                                                            | Impact if ignored                                   |
| -------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| P0       | Auth not wired (`AuthSecurityManager` has no credential verifier; `PasswordManagerFactory` never bootstrapped) | Register/login will fail at runtime                 |
| P0       | `TypesDTO` deterministic IDs ignore `owner_id` + global unique `name`                                          | Cross-tenant type ID collisions                     |
| P0       | API spec fields absent from model (`balance`, `currency`, `category_type`, `transaction_type`, etc.)           | Phantom columns or broken endpoints                 |
| P1       | Pre-user PostgreSQL data: `owner_id NOT NULL` migrations without backfill                                      | `./deploy/alembic.sh upgrade` fails on legacy dumps |
| P1       | `/reports/*` in spec with no read-model strategy                                                               | MVP item #5 cannot be implemented                   |
| P1       | Dual API specs (`API_Endpoints.md.md` + `API_Documentation.md.md`)                                             | Implementers follow conflicting sources             |
| P2       | Package version drift ([#11](https://github.com/Elmorralito/save-ma-money/issues/11))                          | v3 model/API releases out of sync                   |
| P2       | CI has no Alembic PostgreSQL gate                                                                              | Schema regressions ship undetected                  |

### Sub-issues (created)

| Track            | GitHub issue                                                  |
| ---------------- | ------------------------------------------------------------- |
| A — v0 audit     | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) |
| A — v1–v3 schema | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) |
| B — Supabase     | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) |
| C — API spec     | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) |
| D — Migration    | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |

---

## Current state (developer baseline)

### What exists today

| Layer             | Status                                                      | Key paths                                                                                                             |
| ----------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Data model**    | Production-ready ingestion pipeline                         | `modules/model/src/papita_txnsmodel/`                                                                                 |
| **Schema**        | PostgreSQL via Supabase (DuckDB deprecated)                 | `modules/model/src/papita_txnsmodel/database/connector.py`                                                            |
| **Migrations**    | Alembic                                                     | `modules/model/alembic/versions/`                                                                                     |
| **Load handlers** | In model module (registrar module not in current workspace) | `modules/model/src/papita_txnsmodel/handlers/`                                                                        |
| **API**           | Spec + partial scaffold                                     | `modules/api/API_Endpoints.md.md`; implemented: `settings.py`, `security.py` only — no `main.py`, routers, or schemas |
| **Supabase**      | **Not integrated**                                          | No client, auth, or RLS in repo                                                                                       |

### Table inventory (`papita_transactions` schema)

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

### Relationship sketch

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

### What PR #27 and PR #29 changed

- **PR #27:** `users` model, `owner_id` on all entities, extended `BaseRepository` tenant filtering, hash utilities, 4 Alembic migrations.
- **PR #29:** API documentation (`API_Endpoints.md.md`, `API_Documentation.md.md`), `Settings` with `DATABASE_URL` + JWT config, `AuthSecurityManager`. **No FastAPI app, routers, schemas, or live endpoints.**

### Known pain points (with code references)

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

## Goal

Deliver a **frozen v3 target schema** (3NF), a **tenancy strategy** (closing #24), a **Supabase integration decision**, and a **revised API resource map** — so #25 can implement CRUD without rework.

---

## Work tracks

### Track A — Audit and 3NF redesign

#### Step A1: v0 audit document

Create `docs/design/PPT-031-v0-audit.md` covering:

- Every table: columns, PKs, FKs, indexes
- Normalization analysis per table (1NF / 2NF / 3NF violations)
- Query patterns used by repositories and handlers
- Impact on registrar load pipeline

#### Step A2: v1 target schema draft

Propose concrete structural changes. Example directions (pick and justify in the doc):

| Current pattern                                 | Possible simplification                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| `accounts` + `accounts_indexer` + subtype table | Single `accounts` row with `account_kind` enum + optional extension table (1:1) |
| 8 nullable FKs on indexer                       | Typed discriminator + one FK to extension                                       |
| `owner_id` on every child                       | Scope via `accounts.owner_id` or materialized view for hot queries              |
| `identified_transactions` + `transactions`      | Keep split (template vs posted) or merge with `is_template` flag                |

#### Step A3: v2 after API domain review

Incorporate API naming decisions (categories, budgets, movements) into the schema.

#### Step A4: v3 freeze

Final ER diagram in `docs/`, Alembic migration outline, and explicit list of **intentional denormalizations** (if any) with measured rationale.

**Gate:** No API CRUD implementation in #25 until v3 is approved in a comment on this issue.

---

### Track B — Supabase × FastAPI (primary database platform)

**Target platform:** PostgreSQL via **Supabase**. DuckDB is **not** a supported deployment or validation target for PPT-031.

The repo uses **SQLModel + SQLAlchemy** with `DATABASE_URL`. This track produces a **decision record** for Supabase integration and FastAPI wiring.

#### Options to evaluate

| Option                          | Description                                              | Code impact                                                     |
| ------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| **B0 — Local Postgres**         | Docker Postgres for local dev; Supabase for staging/prod | `DATABASE_URL` env docs; same Postgres dialect everywhere       |
| **B1 — Supabase Postgres only** | All environments use Supabase pooler connection string   | Env config + connection string docs                             |
| **B2 — Supabase Auth**          | Replace/bridge JWT auth with Supabase Auth               | Map `auth.users.id` ↔ `papita_transactions.users.id`            |
| **B3 — Supabase Auth + RLS**    | DB-enforced tenant isolation                             | PostgreSQL RLS policies on `owner_id`; Alembic SQL for policies |

#### FastAPI integration points (regardless of option)

| Component               | Current state                                    | Expected work                                               |
| ----------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| `Settings.DATABASE_URL` | Validates via `SQLDatabaseConnector.establish()` | Session dependency for routes                               |
| `AuthSecurityManager`   | JWT generate/decode                              | Login/register routes; optional Supabase token validation   |
| `main.py` / routers     | Empty files                                      | App factory, `/api/v1` router mount, CORS                   |
| Health endpoints        | Spec only                                        | Probe DB with `SELECT 1` or connector health check          |
| Tenant scoping          | `BaseRepository` patterns in model               | API dependency injects `current_user_id` into service calls |

**Default recommendation to document:** **B0 or B1** until v3 schema is frozen (Postgres everywhere). Defer B2/B3 to avoid rewriting auth mid-refactor (PR #27 already invested in `Users` + local JWT). **Do not evaluate DuckDB paths.**

---

### Track C — API spec realignment

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

### Track D — Migration and validation (PostgreSQL / Supabase)

**Database platform:** PostgreSQL via Supabase. **DuckDB is out of scope** for PPT-031 (see [#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

- Write Alembic migrations for v3 (PostgreSQL dialect; expect a new migration series after PR #27's four migrations).
- Provide backfill SQL/scripts for `accounts_indexer` → simplified account structure.
- **FR-14:** Legacy `owner_id` backfill for pre-#26 PostgreSQL data (default user seed or documented wipe-and-reload).
- Run regression on model handlers and `modules/model/tests/`.
- Validate `./deploy/alembic.sh upgrade` on **Docker Postgres** and **Supabase** connection strings.
- Regenerate PostgreSQL ER diagram. [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps) is **superseded** by this platform decision.

---

### Track E — Auth & security contract (prerequisite for #25 MVP)

Define the auth layer end-to-end before implementing `/auth/*` routes.

| Topic            | Current state                                             | Decision needed                                 |
| ---------------- | --------------------------------------------------------- | ----------------------------------------------- |
| Registration     | Spec: `full_name`; model: `username`, `email`, `password` | Unified register schema + response              |
| Login identifier | Form field `username` with email example                  | Login by email, username, or both               |
| Password hashing | Argon2 via `PasswordManagerFactory` (uninitialized)       | Bootstrap in app lifespan / settings            |
| JWT `sub` claim  | String user id in token                                   | Document: UUID string from `Users.id`           |
| Refresh / logout | Spec endpoints exist                                      | Stateless JWT only, or refresh token + denylist |
| API dependencies | Missing `python-multipart` for OAuth2 form login          | Add to `modules/api/pyproject.toml`             |

**Deliverable:** `docs/design/PPT-031-auth-contract.md` covering FR-10, FR-11.

---

### Track F — Reports & read models

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

## Functional requirements (with explanations)

### FR-01 — Target schema satisfies Third Normal Form (3NF)

**Requirement:** The v3 schema must satisfy 3NF unless a specific exception is documented with query-performance or domain-clarity justification.

**Why:** The current schema grew organically (indexer pattern from [PR #12 / PPT-022](https://github.com/Elmorralito/save-ma-money/pull/12), users from PR #27). Normalization reduces update anomalies (e.g. changing `owner_id` in one place vs. 13), simplifies the PostgreSQL FK graph, and makes API DTOs predictable.

**Developer notes:**

- **1NF:** Ensure atomic columns; `tags` as PostgreSQL `ARRAY` is acceptable if treated as atomic multi-value, but document whether tags belong in a junction table for queryability.
- **2NF:** If any table uses composite PKs, ensure no partial dependencies. Example: `financed_asset_accounts` uses composite PK `(bank_credit_liability_account_id, asset_account_id)` — verify all non-key columns depend on the full key.
- **3NF:** Eliminate transitive dependencies. Primary candidate: redundant `owner_id` on child tables when `owner_id` is derivable through FK chains (`transactions → accounts → users`).

**Acceptance:** v0 audit lists each violation; v3 doc lists each resolved violation or documented exception.

---

### FR-02 — Multi-tenant isolation strategy (resolves #24)

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

### FR-03 — Simplify or eliminate `AccountsIndexer`

**Requirement:** Remove `AccountsIndexer` or reduce it to at most one optional extension FK plus an explicit type discriminator.

**Why:** `AccountsIndexer` (`indexers.py`) holds 8 nullable FKs (`asset_account_id`, `liability_account_id`, `banking_asset_account_id`, etc.). Only one should be populated per row, but nothing in the DB enforces that. Repository and DTO code must infer the active subtype manually.

**Developer notes:**

- Preferred patterns: **single-table inheritance** with nullable subtype columns on `accounts`, **class table inheritance** with one 1:1 extension table keyed by `account_id`, or **JSONB extension blob** for rarely queried subtype fields (document 3NF exception if used).
- Migration must map existing indexer rows to the new structure without data loss.
- Update `modules/model/src/papita_txnsmodel/services/indexers.py`, `services/extends.py` (`TypedLinkedEntitiesServiceMixin`), `handlers/factory.py`, and load handlers that depend on indexer resolution.

**Acceptance:** v3 ER diagram has no 8-FK sparse matrix; indexer service removed or reduced to trivial lookup.

---

### FR-04 — Account subtypes without subtype table explosion

**Requirement:** Banking, real estate, trading, bank credit, and credit card accounts must remain representable without requiring six separate physical tables unless each adds substantial non-overlapping columns.

**Why:** Today there are separate tables for each subtype (`banking_asset_accounts`, `real_estate_asset_accounts`, etc.) with overlapping financial columns duplicated from base `assets_accounts` / `liability_accounts`. This increases join complexity and migration cost.

**Developer notes:**

- Audit column overlap across subtype tables in `assets.py` and `liabilities.py`.
- If overlap exceeds ~70%, consolidate shared columns into base table; keep extension tables only for truly unique fields (e.g. `RealEstateAssetAccountsAreaUnits`, `financing_share`).
- Preserve enum types in `enums.py` for domain clarity.

**Acceptance:** v3 table list with column justification per subtype; fewer joins required for "list all accounts for user" query.

---

### FR-05 — Clear semantics for `IdentifiedTransactions` vs `Transactions`

**Requirement:** Document and model the relationship between transaction templates (`identified_transactions`) and posted transactions (`transactions`).

**Why:** `IdentifiedTransactions` holds planned name, value, day-of-month, and `type_id`. `Transactions` holds actual `value`, `transaction_ts`, and optional `from_account_id` / `to_account_id`. The API spec uses "transactions" and "movements" without mapping to these concepts — developers will build the wrong endpoints without clarity.

**Developer notes:**

- Decide: **keep two tables** (budget/recurring template vs ledger entry) or **unify** with `status` / `is_posted` discriminator.
- If kept separate: API should expose `/identified-transactions/*` or nest under accounts; `/movements/*` should not duplicate `/transactions/*` without definition.
- FK: `transactions.identified_transaction_id` is optional — document when it must be set (e.g. recurring match) vs. ad-hoc transactions.

**Acceptance:** Domain glossary in design doc; ER diagram shows cardinality; API spec updated accordingly.

---

### FR-06 — Preserve soft delete and audit fields

**Requirement:** All user-facing entities must retain `active`, `deleted_at`, `created_at`, and `updated_at` via `BaseSQLModel`.

**Why:** The ingestion pipeline and repositories rely on soft delete (`soft_delete_records()`) and conflict resolution. Removing these fields would break registrar reload semantics.

**Developer notes:**

- Inherited from `modules/model/src/papita_txnsmodel/model/base.py`.
- Any new v3 tables must extend `BaseSQLModel`, not raw `SQLModel`.
- **`AccountsIndexer` today uses raw `SQLModel`** — if retained temporarily, migrate to `BaseSQLModel` or document explicit exclusion with rationale.
- API DELETE endpoints should call soft delete, not hard delete, unless admin-only hard delete is explicitly spec'd.

**Acceptance:** v3 schema checklist confirms all user-facing tables extend `BaseSQLModel` patterns.

---

### FR-07 — API resources map 1:1 to v3 model before #25 CRUD work

**Requirement:** Every endpoint in `API_Endpoints.md.md` must map to a v3 DTO/table, or be removed from the spec.

**Why:** PR #29 added a rich API spec (43+ operations) but the model does not support budgets, uses different naming, and routers are empty. Implementing against the current spec will produce orphan endpoints or phantom tables.

**Developer notes:**

- Produce a mapping table: `Endpoint → Router → Service → Repository → DTO → SQLModel`.
- Flag breaking renames early (categories → types).
- Align auth request/response shapes with `Users` model fields.

**Acceptance:** `docs/design/PPT-031-api-model-mapping.md` reviewed and linked from this issue; #25 scoped to MVP list only.

---

### FR-08 — Registrar pipeline compatibility

**Requirement:** The registrar/load handlers must continue to ingest data, or a documented migration path must exist for each breaking schema change.

**Why:** The monorepo's primary production path is registrar → handlers → services → DB (`modules/registrar/`, `modules/model/src/papita_txnsmodel/handlers/`). A simplified schema is useless if CSV/plugin loads break silently.

**Developer notes:**

- Trace handlers: `handlers/base.py`, `handlers/transactions.py`, indexer services.
- For each v3 breaking change, specify: handler update, DTO update, backfill script, or deprecation period.
- Run existing tests in `modules/model/tests/` and registrar tests after migration.

**Acceptance:** Checklist of affected handlers with owner; green test run on sample load after v3 migration applied locally.

---

### FR-09 — Resolve budgets in model or API spec

**Requirement:** Either add first-class budget entities to v3, or remove `/budgets/*` from the API specification.

**Why:** `API_Endpoints.md.md` defines full CRUD for budgets, allocations, and budget summaries. There is **no** `budgets` table in the model. This is the largest spec-vs-model gap.

**Developer notes:**

- If adding budgets: typical model is `budgets` (period, owner_id) + `budget_allocations` (category/type_id, amount) + optional link to `identified_transactions`.
- If deferring: mark `/budgets/*` as "v2 API" in spec and exclude from #25 MVP.
- Do not implement budget endpoints against a non-existent table.

**Acceptance:** Explicit decision in v3 doc; spec updated; #25 MVP excludes budgets if deferred.

---

### FR-10 — Auth credential verification & identity mapping

**Requirement:** Define and implement the contract between API auth routes, `AuthSecurityManager`, and `UsersService`/`UsersDTO`.

**Why:** JWT generation exists but credential verification is not wired. Register cannot hash passwords without initializing `PasswordManagerFactory`. Login field semantics (email vs username) are undefined.

**Developer notes:**

- Add `UsersService.verify_credentials(username_or_email, password) -> UsersDTO | None`.
- Bootstrap `PasswordManagerFactory.get_password_manager(keyword="argon2")` at API startup.
- Document JWT `sub` as the string form of `Users.id` (deterministic uuid5 from username hash today).
- Align `POST /auth/register` request body with `UsersDTO` validators (`USERNAME_REGEX`, `PASSWORD_REGEX`).

**Acceptance:** Auth contract doc merged; register/login sequence diagram; fields mapped in API spec.

---

### FR-11 — JWT refresh, logout, and revocation strategy

**Requirement:** Document how `/auth/refresh` and `/auth/logout` behave, or remove them from MVP spec.

**Why:** Stateless HS256 tokens cannot be invalidated on logout without a denylist, rotation, or refresh-token pair. Spec promises behavior the stack cannot deliver today.

**Developer notes:**

- **Option A:** MVP = access token only; remove refresh/logout from MVP or return 501 with doc note.
- **Option B:** Short-lived access + refresh token stored server-side or in httpOnly cookie.
- **Option C:** Supabase Auth (Track B) owns session lifecycle.

**Acceptance:** Decision recorded; spec updated; #25 MVP scope matches chosen option.

---

### FR-12 — Reports read-model strategy

**Requirement:** Define how `/reports/*` endpoints derive data without new normalized tables unless justified.

**Why:** Reports are read aggregations over transactions, accounts, types, and budgets. No report tables exist; MVP lists reports as item #5 but provides no query design.

**Developer notes:**

- Prefer service-layer queries or SQL views over duplicating data in report tables.
- `budget-performance` blocked until FR-09 budgets decision.
- Document pagination, date filters, and tenant scoping for each report.

**Acceptance:** Report query spec in design doc; MVP report endpoints scoped (full vs stub vs defer).

---

### FR-13 — Category taxonomy mapping

**Requirement:** Resolve semantic gap between API categories and model `Types`.

**Why:** API uses `category_type: income|expense`, hierarchical `parent_id`, and subcategories. Model uses flat `Types` with `TypesClassifications: ASSETS|LIABILITIES|TRANSACTIONS` and globally unique `name`. Renaming `/categories` → `/types` alone is insufficient.

**Developer notes:**

- Map domain concepts explicitly (e.g. expense categories = `Types` where `classification=TRANSACTIONS`).
- Decide if hierarchy requires `parent_id` on `types` or a separate taxonomy table.
- Resolve conflict with FR-15 type identity rules.

**Acceptance:** Taxonomy mapping table in API-model mapping doc; v3 schema change list if hierarchy added.

---

### FR-14 — Legacy data & tenant assignment migration

**Requirement:** Document and implement migration path for pre-user databases and loads with `owner=None`.

**Why:** PR #27 migrations add `owner_id NOT NULL` without backfill. Handlers still allow ownerless loads. Developers with existing pre-#26 PostgreSQL dumps hit upgrade failures.

**Developer notes:**

- Options: seed a `default` system user and backfill; require wipe-and-reload for dev; reject ownerless loads in handlers.
- Include in Track D migration scripts, not only indexer backfill.
- Document in README breaking-change notice for PPT-031.

**Acceptance:** Migration runbook with before/after steps; test upgrade from pre-#26 PostgreSQL snapshot (or documented wipe-and-reload).

---

### FR-15 — Types global vs user-scoped identity rules

**Requirement:** Define uniqueness, ID generation, and write scoping for `types` (`owner_id` nullable).

**Why:** `TypesDTO` generates deterministic IDs without `owner_id`, but `types.name` is globally unique. `TypesRepository` read path merges global + owned types; write path scoping is weaker than `OwnedTableRepository`. User deletion cascade on `owned_types` vs global types is undefined.

**Developer notes:**

- Include `owner_id` (or tenant namespace) in ID hash **or** drop global unique on `name` in favor of composite unique `(owner_id, name, classification)`.
- Align with FR-02 tenancy strategy and FR-13 taxonomy.
- Document behavior when global types exist and user is deleted.

**Acceptance:** Types identity rules in v3 doc; repository tests for two tenants creating same type name.

---

### FR-16 — `FinancedAssetAccounts` integrity

**Requirement:** Clarify cardinality, primary key, and cross-owner constraints for financed asset joins.

**Why:** PK is only `bank_credit_liability_account_id` (one credit → one asset; one asset may have many credits). `financing_share` has no sum-to-1 constraint. Join table carries redundant `owner_id` without DB check that asset, liability, and join owners match. DTO default `financing_share=0.0` violates `gt=0`.

**Developer notes:**

- Decide composite PK `(asset_account_id, bank_credit_liability_account_id)` if many-to-many needed.
- Add CHECK constraints or service validation for owner consistency and share totals.
- Fix DTO default to satisfy validators.

**Acceptance:** ER diagram updated; constraints listed in v3 migration plan.

---

### FR-17 — API schema layer & OpenAPI source of truth

**Requirement:** Choose a single API specification source and define Pydantic schema strategy for #25.

**Why:** Two markdown specs exist (`API_Endpoints.md.md`, `API_Documentation.md.md`) plus aspirational README structure. No `schemas/`, routers, or OpenAPI JSON. FastAPI deps missing `python-multipart` for form login.

**Developer notes:**

- Consolidate to one spec; generate or maintain OpenAPI from FastAPI app as source of truth going forward.
- Rule: API schemas in `papita_txnsapi/schemas/` map to model DTOs — no duplicate business validation logic.
- Add missing dependencies before auth routes.

**Acceptance:** Single spec file marked canonical; schema mapping rules in API README; OpenAPI export plan for #25.

---

## Non-functional requirements (with explanations)

### NFR-01 — Alembic migrations with rollback notes

**Requirement:** All schema changes ship as Alembic revisions in `modules/model/alembic/versions/` with documented downgrade path.

**Why:** PPT-031 targets **PostgreSQL via Supabase** only. Migrations must be PostgreSQL-compatible (Supabase uses standard Postgres).

**Developer notes:**

- Name migrations with date prefix convention already in repo.
- Test: `./deploy/alembic.sh upgrade` and `downgrade -1` on Docker Postgres and Supabase staging.
- Large data backfills: separate data migration script, not only DDL.
- Remove or deprecate DuckDB-specific Alembic branches in a follow-up cleanup PR (out of PPT-031 design scope).

**Acceptance:** Migration PR includes upgrade/downgrade test log in description.

---

### NFR-02 — Local development on PostgreSQL / Supabase

**Requirement:** Simplified schema must remain developable locally using PostgreSQL tooling.

**Why:** Local dev uses Docker Postgres (`docker/database/docker-compose.yml`) or a Supabase project connection string. DuckDB file storage (`.data/store.duckdb`) is **deprecated** for this project.

**Developer notes:**

- `DATABASE_URL` must point to a PostgreSQL-compatible endpoint (Docker or Supabase pooler).
- Verify column types work on Postgres (e.g. `ARRAY`, `DECIMAL`, UUID).
- Document Supabase env vars: `DATABASE_URL`, optional `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- RLS policies (B3) apply on Supabase/Postgres; test with policy-enabled staging DB.

**Acceptance:** README or design doc "Local dev" section updated for Supabase/Postgres-only workflow.

---

### NFR-03 — Preserve layered architecture

**Requirement:** Keep Model → Access (DTO/Repository) → Service → Handler/API separation.

**Why:** Project conventions (`.cursor/rules`, module READMEs) enforce this pattern. API routes must not embed raw SQL; they call services that use repositories.

**Developer notes:**

- New v3 entities need: SQLModel in `model/`, DTO in `access/`, repository, service, optional handler, API schema + router.
- Reuse `BaseRepository`, `BaseService`, `check_expected_dto_type()`.

**Acceptance:** Architecture review checklist in PR template for v3 implementation PRs.

---

### NFR-04 — Cross-tenant access denial tests

**Requirement:** Automated tests must prove User A cannot access User B's records.

**Why:** Financial data isolation is a security requirement, not only a data modeling concern. PR #27 added `owner_id` but comprehensive denial tests may not cover all repositories.

**Developer notes:**

- Add integration tests: create two users, seed data, assert 404 or empty result when querying other tenant's IDs.
- If RLS: test with Postgres policy enabled.
- Cover at minimum: accounts, transactions, types.

**Acceptance:** Test module or marked test cases listed in v3 implementation PR.

---

### NFR-05 — Secrets via environment variables only

**Requirement:** `DATABASE_URL`, `JWT_SECRET_KEY`, and any Supabase keys must load from env / `.env`, never committed.

**Why:** `Settings` in `modules/api/src/papita_txnsapi/config/settings.py` already uses `pydantic-settings` with `.env`. Supabase introduces `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — same rule applies.

**Developer notes:**

- Update `.env.example` if new vars added (do not commit real `.env`).
- Document in API README which vars are required per deployment option (B0–B3).

**Acceptance:** No secrets in diff; example env documented.

---

### NFR-06 — Updated ER diagram and API mapping documentation

**Requirement:** Ship updated ER diagram and endpoint-to-model mapping in `docs/`.

**Why:** Existing diagram `docs/postgres_papita_transactions.png` predates users and simplification. Developers and API implementers need a single visual source of truth.

**Developer notes:**

- Regenerate Postgres ER after v3 migration on Docker.
- Add `docs/design/PPT-031-api-model-mapping.md` as tabular complement to ER.

**Acceptance:** Files linked in issue comment at v3 freeze.

---

### NFR-07 — PostgreSQL FK integrity on simplified schema

**Requirement:** v3 schema must create a complete, valid FK graph on PostgreSQL (Supabase).

**Why:** Simplifying the schema (especially removing the `AccountsIndexer` sparse FK matrix) should yield a cleaner ER diagram and reliable constraint enforcement on the sole supported platform.

**Developer notes:**

- After v3 migration, run `./deploy/alembic.sh upgrade` against Docker Postgres and Supabase staging.
- Regenerate ER diagram; verify all expected FKs exist.
- Supersedes [#17](https://github.com/Elmorralito/save-ma-money/issues/17) (DuckDB FK gaps — no longer applicable).

**Acceptance:** ER diagram + FK checklist attached to [#34](https://github.com/Elmorralito/save-ma-money/issues/34) migration PR.

---

### NFR-08 — Password manager bootstrap

**Requirement:** Application startup must initialize `PasswordManagerFactory` before any `UsersDTO` serialization.

**Why:** Without `get_password_manager(keyword="argon2")`, registration raises at runtime when hashing passwords.

**Developer notes:** Wire in FastAPI lifespan or `Settings` model validator; add unit test in model or API test suite.

**Acceptance:** Test creates user via DTO serialize path without error.

---

### NFR-09 — CI test matrix & Alembic PostgreSQL gate

**Requirement:** CI must reflect modules that exist and gate schema changes on PostgreSQL where feasible.

**Why:** Root `pyproject.toml` references `./modules/api/tests` and `./modules/registrar/tests` but only `modules/model/tests/` exists. No CI job runs `./deploy/alembic.sh upgrade` on PostgreSQL.

**Developer notes:**

- Fix testpaths or add placeholder tests; add optional CI job for Alembic upgrade on Docker Postgres (and Supabase staging if secrets available).
- v3 PRs include migration test log in description until CI job exists.

**Acceptance:** CI config updated or tracking issue linked; manual gate documented for v3 migration PRs.

---

### NFR-10 — PostgreSQL upsert behavior

**Requirement:** Document and test upsert behavior on PostgreSQL after schema changes.

**Why:** Load handlers and repositories use `PostgreSQLUpserter` for idempotent ingestion. With DuckDB deprecated, upsert tests target Postgres only.

**Developer notes:** Add integration test against Docker Postgres or document upsert SQL in v0 audit. Legacy `DuckDBUpserter` code may be removed in a separate cleanup PR.

**Acceptance:** Upsert behavior noted in design docs; regressions tested if upsert-heavy paths change.

---

### NFR-11 — Package & repo version alignment ([#11](https://github.com/Elmorralito/save-ma-money/issues/11))

**Requirement:** v3 schema release must coordinate model and API package versions per monorepo policy.

**Why:** Model `0.1.13a28`, API `0.0.3a14`, root `v0.0.1`. API `pyproject.toml` pins published model range, not local path dep — v3 breaking changes may not propagate in CI.

**Developer notes:**

- Bump model semver for breaking schema; bump API to match.
- Document coupling rule: API depends on exact model version for v3 release train.
- Coordinate with [#11](https://github.com/Elmorralito/save-ma-money/issues/11).

**Acceptance:** Version bump plan in v3 sign-off comment; #11 referenced.

---

### NFR-12 — Model & documentation consistency

**Requirement:** v3 refactor includes cleanup of known doc/model drift before freeze.

**Why:** Incorrect docstrings and TYPE_CHECKING imports (`Assets` vs `AssetAccounts`, `LiabilityAccounts` fields) cause unsafe refactors during simplification.

**Developer notes:** Add to v3 PR checklist: docstrings match fields; TYPE_CHECKING imports correct; interrogate/doc coverage maintained.

**Acceptance:** Known drift items from pain point #6 resolved or tracked with issue links.

---

## Issue dependencies

| Issue                                                                                                                       | Relationship                                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| [#26](https://github.com/Elmorralito/save-ma-money/issues/26)                                                               | Done — baseline for this work                                                                                                       |
| [#24](https://github.com/Elmorralito/save-ma-money/issues/24)                                                               | Close when FR-02 tenancy strategy is approved                                                                                       |
| [#25](https://github.com/Elmorralito/save-ma-money/issues/25)                                                               | Blocked until v3 schema + API mapping approved                                                                                      |
| [#17](https://github.com/Elmorralito/save-ma-money/issues/17)                                                               | **Superseded** — DuckDB deprecated; closed; Postgres FK validation in [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |
| [#11](https://github.com/Elmorralito/save-ma-money/issues/11)                                                               | Coordinate version bumps at v3 release (NFR-11)                                                                                     |
| [#30](https://github.com/Elmorralito/save-ma-money/issues/30)–[#34](https://github.com/Elmorralito/save-ma-money/issues/34) | Implementation sub-issues for tracks A–D                                                                                            |

---

## Sub-issues

| ID        | GitHub                                                        | Title                                              | Track |
| --------- | ------------------------------------------------------------- | -------------------------------------------------- | ----- |
| PPT-031-A | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) | Data model audit and 3NF gap analysis (v0)         | A     |
| PPT-031-B | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) | Target schema iterations v1–v3 + ER diagram        | A     |
| PPT-031-C | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) | Supabase × FastAPI decision record                 | B     |
| PPT-031-D | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) | API spec realignment (`API_Endpoints.md.md`)       | C     |
| PPT-031-E | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) | Alembic migration + Supabase PostgreSQL validation | D     |

Tracks **E** (auth) and **F** (reports) are scoped in this issue; implement via #33 (spec) and #25 (code) after v3 freeze.

---

## Acceptance criteria (issue closure)

- [x] `docs/design/PPT-031-v0-audit.md` merged ([#30](https://github.com/Elmorralito/save-ma-money/issues/30))
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

## References

### GitHub

- [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — parent issue
- [#30](https://github.com/Elmorralito/save-ma-money/issues/30)–[#34](https://github.com/Elmorralito/save-ma-money/issues/34) — sub-issues
- PR [#27](https://github.com/Elmorralito/save-ma-money/pull/27) — users + `owner_id`
- PR [#29](https://github.com/Elmorralito/save-ma-money/pull/29) — API spec + scaffold

### Repo documents

- [`docs/issues/README.md`](./README.md) — issue document index
- [`docs/design/README.md`](../design/README.md) — design document registry
- [`docs/design/PPT-031-v0-audit.md`](../design/PPT-031-v0-audit.md) — [#30](https://github.com/Elmorralito/save-ma-money/issues/30)
- [`docs/issues/PPT-031-C-supabase-decision-brief.md`](./PPT-031-C-supabase-decision-brief.md) — [#31](https://github.com/Elmorralito/save-ma-money/issues/31)

### Code

- Model: `modules/model/src/papita_txnsmodel/model/`
- Indexer: `modules/model/src/papita_txnsmodel/model/indexers.py`
- API spec: `modules/api/API_Endpoints.md.md`
- Settings: `modules/api/src/papita_txnsapi/config/settings.py`
- Auth: `modules/api/src/papita_txnsapi/core/security.py`
- ER (current): `docs/postgres_papita_transactions.png`
- Alembic: `modules/model/alembic/`, `deploy/alembic.sh`
