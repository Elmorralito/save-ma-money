# PPT-031-E: Migration runbook (Track D — [#34](https://github.com/Elmorralito/save-ma-money/issues/34))

> **Status:** v3 seed revision `a75354933e79` — single baseline migration; legacy v0 chain removed (2026-07-07).
> **Platform:** PostgreSQL only (Docker local, Supabase pooler for hosted). DuckDB is deprecated.

## Document map

| Section                                                              | Scope                                    |
| -------------------------------------------------------------------- | ---------------------------------------- |
| [§1 Executive summary](#1-executive-summary)                         | Current state, gates, deliverable status |
| [§2 Gap analysis](#2-gap-analysis-current-v0--target-v3)             | Table-by-table v0 → v3                   |
| [§3 v0 migration path (historical)](#3-v0-migration-path-historical) | Pre-squash FR-14 notes (archived)        |
| [§4 v3 seed migration](#4-v3-seed-migration)                         | Baseline revision `a75354933e79`         |
| [§5 Validation](#5-validation)                                       | Local Docker + Supabase + CI             |
| [§6 Rollback](#6-rollback)                                           | Downgrade notes                          |
| [§7 Risks & decisions](#7-risks--decisions)                          | FR-14 strategy, idempotency              |

**Source of truth for v3 target:** [`PPT-031-v1-schema.md`](PPT-031-v1-schema.md) §3–§6.

---

## 1. Executive summary

### What #34 requires

| ID                   | Deliverable                                       | Status                                                                            |
| -------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| **NFR-01**           | Alembic revisions with PostgreSQL downgrade notes | ✅ `a75354933e79` v3 seed (reversible)                                            |
| **FR-14**            | Legacy `owner_id` backfill for pre-#26 dumps      | **N/A** — v0 chain removed; use wipe-and-reload                                   |
| **FR-08**            | Handler/load pipeline regression tests            | ✅ 260 tests; v3 handlers                                                         |
| **NFR-04**           | Cross-tenant denial tests                         | ✅ `test_owned_table_repository.py`                                               |
| **NFR-09**           | CI Alembic PostgreSQL gate                        | ✅ `migration-check.yml`                                                          |
| **Indexer backfill** | `accounts_indexer` → v3 accounts                  | **N/A** — no v0 data path                                                         |
| **G8**               | ER diagram from live DB                           | Design SVG; post-migration PNG pending                                            |
| **RLS (B3)**         | Supabase policy migrations                        | **Deferred** per [#31](https://github.com/Elmorralito/save-ma-money/issues/31) G7 |

### Gates

| Gate                         | Status                                                                                                      | Notes                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **G1** — v3 schema freeze    | **Implemented** (awaiting formal sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)) | Code follows `PPT-031-v1-schema.md` §3–§5        |
| **G6** — Legacy data (FR-14) | **Superseded**                                                                                              | Squashed to v3 seed; dev DBs use wipe-and-reload |

### Current migration head

```
a75354933e79 (ppt_031_v3_seed_version)   ← HEAD (v3 baseline)
```

### v3 migration artifacts

| File                                                                       | Purpose                                                                                                                              |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `alembic/versions/2026_07_07_2325-a75354933e79_ppt_031_v3_seed_version.py` | Full v3 schema: 11 tables, enums, CHECK constraints, `account_balances` mat. view (`alembic_utils`), `uq_categories_owner_name_kind` |

### Account value semantics (`initial_value` vs `balance`)

| Field / view               | Source                                            | When to use                                  |
| -------------------------- | ------------------------------------------------- | -------------------------------------------- |
| `accounts.initial_value`   | Stored on account row                             | Opening cost basis at create time            |
| `accounts.current_value`   | Stored snapshot                                   | Illiquid assets (real estate, brokerage NAV) |
| `account_balances.balance` | Materialized view from **COMPLETED** transactions | Cash-like assets; ledger-derived             |

`initial_value` is **not** included in `account_balances`. To align ledger balance with an opening amount, post an opening `INCOME`, `EXPENSE`, or `TRANSFER` transaction (or ingest equivalent rows) before reading the view.

After transaction upserts, `TransactionsService.upsert_records(..., refresh_balances=True)` refreshes all balance materialized views via `refresh_balance_materialized_views()` (`account_balances`, `owner_yearly_balances`, `owner_monthly_balances`, `owner_quarterly_balances`, `owner_biannual_balances`). For bulk loads, pass `refresh_balances=False` and call `refresh_balance_materialized_views(connector)` once at the end (unique indexes required for concurrent refresh).

### Balance report MV indexes

Index definitions are centralized in `papita_txnsmodel/views/indexes.py` (not managed by `alembic_utils` `PGMaterializedView`). Migrations apply specs via `op.create_index` / `op.drop_index`.

Table indexes are declared on SQLModel entities (`accounts`, `transactions`, `transaction_templates`, `account_financing`, `categories`) and applied via Alembic revision `f3a4b5c6d7e8`.

| Index kind       | Columns (typical)                                           | Purpose                                                        |
| ---------------- | ----------------------------------------------------------- | -------------------------------------------------------------- |
| Primary unique   | tenant + period keys + `currency`                           | Fetch by filter path; `REFRESH MATERIALIZED VIEW CONCURRENTLY` |
| Fetch support    | `(owner_id, currency)`                                      | Owner + currency YAML filter without period/account keys       |
| Table (ledger)   | `(owner_id, active, status)`, account FKs on `transactions` | MV refresh + tenant ledger joins                               |
| Table (accounts) | `(owner_id, active)`                                        | Active account listings per tenant                             |

Fetch SQL is built in `access/balance_reports/query_sql.py` (shared with `BalanceReportsRepository`).

### Scheduled MV refresh (feasibility)

| Option                    | Supported   | Notes                                                                                      |
| ------------------------- | ----------- | ------------------------------------------------------------------------------------------ |
| Event-driven (current)    | ✅          | `refresh_balance_materialized_views()` after transaction upsert                            |
| `alembic_utils` scheduler | ❌          | Library manages entity DDL only; no cron/refresh scheduling                                |
| PostgreSQL `pg_cron`      | ⚠️ Optional | Requires extension + host support; schedule `REFRESH MATERIALIZED VIEW` SQL in a migration |
| App scheduler             | ⚠️ Optional | Cron/worker calls `refresh_balance_materialized_views()`; no schema change                 |

**Recommendation:** keep event-driven refresh as default; add `pg_cron` or an app scheduler only if latency SLA requires time-based staleness bounds.

### Transactions table partitioning

`transactions` is partitioned **monthly** on `transaction_ts` (PostgreSQL `RANGE`), revision `g4b5c6d7e8f9`. Composite primary key `(id, transaction_ts)`; non-unique `ix_transactions_id` supports id-only lookups. Child partitions use `transactions_yYYYYmMM`; Alembic `include_object` ignores them for drift checks.

| Setting        | Value                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------- |
| Retention      | **10 years** — older monthly partitions are dropped by maintenance                           |
| Future buffer  | **12 months** ahead — created by maintenance                                                 |
| Maintenance    | `./deploy/transaction_partitions.sh` (requires `DATABASE_URL`)                               |
| Implementation | Plain Alembic SQL + `papita_txnsmodel/config/transaction_partitions.py` (no `alembic_utils`) |

Schedule maintenance (cron / worker) monthly: create upcoming partitions before inserts arrive, archive/drop expired partitions after backup if required.

---

## 2. Gap analysis (current v0 → target v3)

### Table mapping

| v0 table (14)                    | v3 table (11)                  | Migration step                                                                                 |
| -------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `users`                          | `users`                        | Retain; column cleanup done in `ccaa69123f7e`                                                  |
| `accounts`                       | `accounts`                     | M-02 + M-08: merge financial cols from subtypes; add `account_kind`, `ledger_side`, `currency` |
| `accounts_indexer`               | —                              | **Dropped** — kind derived from populated subtype FKs (§5.3.2)                                 |
| `types`                          | `categories`                   | M-04 + §5.3.3: TRANSACTIONS → categories; ASSETS/LIABILITIES → `account_kind`                  |
| `assets_accounts`                | `accounts` cols                | Merged into `accounts`                                                                         |
| `liability_accounts`             | `accounts` cols                | Merged into `accounts`                                                                         |
| `banking_asset_accounts`         | `banking_account_details`      | M-03 extension 1:1                                                                             |
| `real_estate_asset_accounts`     | `real_estate_account_details`  | M-03                                                                                           |
| `trading_asset_accounts`         | `trading_account_details`      | M-03                                                                                           |
| `credit_card_liability_accounts` | `credit_card_account_details`  | M-03                                                                                           |
| `bank_credit_liability_accounts` | `loan_account_details`         | M-03                                                                                           |
| `financed_asset_accounts`        | `account_financing`            | M-07 + §5.3.7: composite PK; resolve via indexer                                               |
| `identified_transactions`        | `transaction_templates`        | M-05 + §5.3.4                                                                                  |
| `transactions`                   | `transactions`                 | M-06 + §5.3.6: add `transaction_kind`, `category_id`, `amount`, `currency`, `status`           |
| —                                | `account_balances` (mat. view) | M-11 after rename                                                                              |

### Column-level gaps (high impact)

| Area              | v0                        | v3                                                  | Backfill risk                                        |
| ----------------- | ------------------------- | --------------------------------------------------- | ---------------------------------------------------- |
| Account typing    | 8 nullable indexer FKs    | `account_kind` ENUM                                 | Ambiguous rows (multiple FKs set) need manual review |
| Transaction shape | `value`, optional from/to | `amount`, `transaction_kind`, CHECK constraints     | Income/expense/transfer inference from FK pattern    |
| Categories        | `types.classification`    | `categories.category_kind` INCOME/EXPENSE           | Heuristic name matching (§5.3.3)                     |
| Balances          | Snapshot on subtype rows  | `account_balances` mat. view + opening-balance rows | NF-06 carry-forward (§5.3.8)                         |
| Financing         | Subtype-row FKs           | `accounts.id` composite PK                          | Requires indexer join (§5.3.7)                       |

### Code gaps (post-v3)

| Layer                  | v0 paths           | v3 change                                   |
| ---------------------- | ------------------ | ------------------------------------------- |
| `model/indexers.py`    | `AccountsIndexer`  | Remove                                      |
| `model/types.py`       | `Types`            | Replace with `categories`                   |
| `access/indexers/`     | DTO + repository   | Remove; fold into accounts                  |
| `handlers/`            | Indexer-aware load | `owner=` mandatory; simplified account load |
| `services/indexers.py` | Indexer service    | Remove                                      |

---

## 3. v0 migration path (historical)

> **Archived:** The v0 Alembic chain (`93420bed0a90` … `ccaa69123f7e`) and v0→v3 backfill SQL were removed when the schema was squashed to seed revision `a75354933e79`. Existing v0 PostgreSQL dumps cannot upgrade in-place; use wipe-and-reload or a one-off ETL script.

### FR-14: Pre-#26 PostgreSQL upgrade (archived)

**Problem:** Revision `06b97dfcb5c7` originally added `owner_id NOT NULL` directly, causing upgrade failures on dumps with existing rows but no `users` table.

**Fix (implemented):** Three-phase pattern in `06b97dfcb5c7`:

1. Create `users` table.
2. Seed **legacy migration user** (`00000000-0000-0000-0000-000000000001`).
3. For each tenant table: add `owner_id` **nullable** → `UPDATE` backfill → `ALTER NOT NULL` → FK + index.

#### Legacy user seed

| Field      | Value                                                   |
| ---------- | ------------------------------------------------------- |
| `id`       | `00000000-0000-0000-0000-000000000001`                  |
| `username` | `legacy_migration`                                      |
| `email`    | `legacy@local.invalid`                                  |
| `password` | `UNSET_MIGRATION_PLACEHOLDER` (must reset before login) |

> **Security:** This user exists only to satisfy FK constraints during migration. Disable or delete after reassigning data to real users.

#### Before upgrade (pre-#26 snapshot)

```bash
# 1. Backup
pg_dump "$DATABASE_URL" -Fc -f papita_pre_ppt031.dump

# 2. Confirm revision before users migration
cd modules/model && poetry run alembic -c alembic.ini -x "dbUrl=$DATABASE_URL" current
# Expected: 53fec3d56681 (or earlier)

# 3. Upgrade
/bin/bash ./deploy/alembic.sh upgrade --url "$DATABASE_URL"
```

#### After upgrade — reassign ownership

```sql
-- Example: move all legacy-tagged rows to a real user
UPDATE papita_transactions.accounts
SET owner_id = '<real-user-uuid>'
WHERE owner_id = '00000000-0000-0000-0000-000000000001';
-- Repeat for child tables in FK dependency order, or use CASCADE-aware script
```

#### Wipe-and-reload alternative

For development databases with no retention requirement:

```bash
docker compose -f docker/database/docker-compose.yml down -v
docker compose -f docker/database/docker-compose.yml up -d
/bin/bash ./deploy/alembic.sh upgrade
# Reload via registrar/handler pipeline with explicit owner=
```

---

## 4. v3 seed migration

Revision **`a75354933e79`** (`ppt_031_v3_seed_version`) creates the full v3 schema in one step:

| Component   | Details                                                                                                                                                                 |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema      | `papita_transactions` + PostgreSQL extensions (`uuid-ossp`, `pgcrypto`)                                                                                                 |
| Tables      | 11 v3 tables autogenerated from SQLModel                                                                                                                                |
| Constraints | `accounts_ledger_side_matches_kind`, `chk_transaction_kind_accounts`, `chk_financing_share`                                                                             |
| View        | Balance report MVs under `papita_txnsmodel/views/balance_reports/` (SQL + `views.py` entities), registered via [alembic_utils](https://pypi.org/project/alembic_utils/) |

**Downgrade:** drops mat. view, all tables, enums, and schema (`CASCADE`). Fully reversible for CI round-trip.

### Remaining post-migration

- **§5.3.8** opening-balance carry-forward — deferred; run after mat. view refresh
- **G8** — regenerate PNG ER from live DB
- **Supabase** — pooler validation per §5

---

## 5. Validation

### Local Docker Postgres

```bash
docker compose -f docker/database/docker-compose.yml up -d

# Full upgrade (Docker Postgres is default)
/bin/bash ./deploy/alembic.sh upgrade

# Round-trip test (mirrors CI)
export DB_URL="postgresql+psycopg2://<user>:<pass>@localhost:5432/<db>"
/bin/bash .github/scripts/migration_check.sh

# Model tests
poetry run pytest modules/model/tests/
```

### Supabase (pooler)

Use **transaction mode** pooler (`:6543`) for app runtime; **session mode** (`:5432`) for DDL migrations if pooler rejects multi-statement DDL.

```bash
export DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres"
/bin/bash ./deploy/alembic.sh upgrade --url "$DATABASE_URL"
```

> Never commit real credentials. Copy formats from [`.env.example`](../../.env.example).

### CI gate (NFR-09)

Workflow: [`.github/workflows/migration-check.yml`](../../.github/workflows/migration-check.yml)

Steps executed by [`migration_check.sh`](../../.github/scripts/migration_check.sh):

1. `alembic upgrade head`
2. `alembic downgrade -1`
3. `alembic upgrade head`
4. `alembic check` (model drift)

**Recommendation:** Keep path filters on `modules/model/alembic/**` and `modules/model/src/papita_txnsmodel/model/**`. Extend to run on PRs touching `deploy/alembic.sh` (already included).

### ER diagram refresh (G8)

After v3 migration on live DB:

```bash
# Example: schemaSpy, pgModeler, or DBeaver export to docs/postgres_papita_transactions_v3_live.png
# Design-time SVG already at docs/postgres_papita_transactions_v3.svg
```

---

## 6. Rollback

### v3 seed revision

| Revision       | Downgrade action                                                                     |
| -------------- | ------------------------------------------------------------------------------------ |
| `a75354933e79` | Drop `account_balances` mat. view, all v3 tables/enums, `papita_transactions` schema |

### Historical v0 chain (removed)

The pre-squash revisions are no longer in the repository. Production rollback requires restoring a database snapshot taken before the squash deploy.

---

## 7. Risks & decisions

| Risk                                          | Mitigation                                                                                                                                                                                                |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ambiguous indexer rows (multiple subtype FKs) | Quarantine table + manual review queue in M-08                                                                                                                                                            |
| Transfer transactions as two one-sided rows   | Merge to single TRANSFER row per §5.3.6                                                                                                                                                                   |
| Opening balance ≠ ledger sum                  | Post opening transaction or use `current_value` for illiquid assets; see [§4 account value semantics](#account-value-semantics-initial_value-vs-balance); `TransactionsService` refreshes MV after upsert |
| Legacy user left active                       | Document post-migration reassignment; block login for placeholder password                                                                                                                                |
| G1 changes after implementation starts        | Freeze §5.3 SQL; implement only after sign-off comment on #28                                                                                                                                             |
| Downgrade on production                       | Discourage; snapshot + forward-only for prod                                                                                                                                                              |

### FR-14 decision (locked for v0)

**Default:** Seed `legacy_migration` user + backfill all NULL `owner_id` to seed UUID.

**Alternative:** Wipe-and-reload for dev environments (documented above).

### Idempotency

- Legacy user insert: `ON CONFLICT DO NOTHING`
- Backfill `UPDATE`: `WHERE owner_id IS NULL` only
- v3 category seeds: `ON CONFLICT DO NOTHING` per §5.3.5

---

## References

- [#34](https://github.com/Elmorralito/save-ma-money/issues/34) — Track D issue
- [#32](https://github.com/Elmorralito/save-ma-money/issues/32) / [`PPT-031-v1-schema.md`](PPT-031-v1-schema.md) — v3 target + §5 outline
- [#30](https://github.com/Elmorralito/save-ma-money/issues/30) / [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md) — v0 baseline
- [#31](https://github.com/Elmorralito/save-ma-money/issues/31) — Supabase B0/B1 decision
- [`PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md) — FR/NFR traceability
- [`AGENTS.md`](../../AGENTS.md) — Alembic wrapper commands
