# Architecture — save-ma-money

The codemap: where things happen, coarse module by coarse module — a map of a country, not an atlas. Keep it concise; name modules and invariants; avoid deep links that go stale (use search). Detail lives in `architecture/<slug>.md`, indexed below.

## Map

- **`modules/model`** — `papita_txnsmodel`: SQLModel tables under `src/papita_txnsmodel/model/` (composite indexes on `accounts`, `transactions`, `transaction_templates`, `account_financing`), DTOs/repositories in `access/`, business logic in `services/`, loaders in `handlers/`. Balance report MVs in `views/balance_reports/` (SQL + `views.py` entities); MV fetch indexes in `views/indexes.py`. Generic balance report reads: `config/data/balance_report_filters.yaml`, `config/balance_report_specs.py`, `access/balance_reports/`, `services/balance_reports.py`, `handlers/balance_reports.py`. Partition + MV registry: `config/transaction_partitions.py`, `config/materialized_views.py`. Alembic under `alembic/`.
- **`modules/api`** — `papita_txnsapi`: FastAPI app — health ([#45](https://github.com/Elmorralito/save-ma-money/issues/45)) including `/health/database` (API↔DB latency probe via `core/db_health.probe_database`) and optional Redis probes (`core/redis`, PPT-043 / [#83](https://github.com/Elmorralito/save-ma-money/issues/83)); auth + tenant ([#44](https://github.com/Elmorralito/save-ma-money/issues/44)); **accounts + categories CRUD** ([#46](https://github.com/Elmorralito/save-ma-money/issues/46)); transactions/movements ([#47](https://github.com/Elmorralito/save-ma-money/issues/47)); **reports** ([#48](https://github.com/Elmorralito/save-ma-money/issues/48)). Optional Redis for cache-aside + distributed auth rate limits (`REDIS_*` settings; in-memory fallback when disabled).
- **`deploy/`** — shared shell utilities, `alembic.sh`, `test.sh`, `transaction_partitions.sh` (monthly partition ensure + retention archive).
- **`docker/`** — local PostgreSQL 15 + Redis 7 via Compose for B0 API/dev (`docker/docker-compose.yml`, `docker/database/`).

Registrar package is referenced in pytest config but not present in the tree yet.

## v3 data model (PPT-031)

Schema `papita_transactions` — **11 tables** + materialized view `account_balances`:

| Table                                              | Purpose                                                                                                                                                                                                                           |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `users`                                            | Tenant root                                                                                                                                                                                                                       |
| `accounts`                                         | Consolidated accounts (`account_kind`, `ledger_side`, `currency`, `initial_value`, `current_value`)                                                                                                                               |
| `categories`                                       | Income/expense taxonomy (`parent_id`, `category_kind`)                                                                                                                                                                            |
| `transaction_templates`                            | Recurring/planned templates                                                                                                                                                                                                       |
| `transactions`                                     | Posted ledger (`transaction_kind`, `from_account_id`, `to_account_id`, `category_id`); **monthly RANGE(`transaction_ts`)** partitions (10-year retention; `config/transaction_partitions.py`, `deploy/transaction_partitions.sh`) |
| `banking_account_details` … `loan_account_details` | 1:1 account extensions (5 tables)                                                                                                                                                                                                 |
| `account_financing`                                | Asset–loan financing links                                                                                                                                                                                                        |
| `account_balances` (MV)                            | Per-account ledger balances; SQL in `views/balance_reports/account_balances.sql`                                                                                                                                                  |
| `owner_yearly_balances` (MV)                       | Per-owner combined yearly totals across all accounts (by currency)                                                                                                                                                                |
| `owner_monthly_balances` (MV)                      | Per-owner combined monthly report balances                                                                                                                                                                                        |
| `owner_quarterly_balances` (MV)                    | Per-owner combined quarterly report balances                                                                                                                                                                                      |
| `owner_biannual_balances` (MV)                     | Per-owner combined semi-annual (H1/H2) report balances                                                                                                                                                                            |

Removed v0: `accounts_indexer`, `types`, `assets_*`, `liabilities_*`, `identified_transactions` (renamed to `transaction_templates`).

## Handlers (ingest)

`HandlerFactory.load("papita_txnsmodel.handlers")` registers:

- `UsersTableHandler`, `AccountsTableHandler`, `CategoriesTableHandler`
- `TransactionTemplatesTableHandler`, `TransactionsHandler`
- Five `*_account_details` handlers + `AccountFinancingTableHandler`
- `BalanceReportsHandler` — read-only balance report export (`balance_reports`, `balance_report`, `reports`)
- Legacy registrar labels (`types`, `identified_transactions`) → `DeprecationWarning` via `handlers/compat.py`

## Balance reports (read)

YAML registry: `papita_txnsmodel/config/data/balance_report_filters.yaml` (five `report_id`s). Unregistered views raise `UnregisteredBalanceReportError` and cannot be queried. `BalanceReportsService` / `BalanceReportsHandler` expose `list_reports()`, filter specs, and `get_report_data(report_id, owner, filters)`. MV fetch indexes: `views/indexes.py` (Alembic-applied; not `alembic_utils` autogenerate). Refresh: event-driven on transaction writes (`balance_views.py` via `TransactionsService.create` / `delete` / `upsert_records`); time-based refresh not supported by `alembic_utils` (see runbook).

## API-readiness services (PPT-041)

Model-layer endpoints for PPT-032 wire through:

| Service                              | Module                      | Role                                                                                                            |
| ------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `AccountsService`                    | `services/accounts.py`      | CRUD + `create_account` / `update_account` extension orchestration by `account_kind`; `get_balance`             |
| `TransactionsService`                | `services/transactions.py`  | CRUD + `list_transfers`, `create_transfer`, `complete_transfer`, `cancel`                                       |
| `ReportService`                      | `services/reports.py`       | Tenant-scoped `spending` / `cash_flow` / `trends` / `export` (FR-12); requires `owner=`; validates `account_id` |
| `refresh_balance_materialized_views` | `services/balance_views.py` | Shared MV refresh helper (exported from `services/__init__.py`; used by cash-flow G9)                           |

Extension routing map: `services/account_extension_routing.py`. Live-DB tenancy tests: `tests/tests_papita_txnsmodel/integration/` (require `DATABASE_URL` PostgreSQL).

## API routers (PPT-036–038)

| Router prefix          | Module                       | Service delegation                                                               |
| ---------------------- | ---------------------------- | -------------------------------------------------------------------------------- |
| `/api/v1/accounts`     | `routers/v1/accounts.py`     | `AccountsService` — CRUD, extensions (G1), balance (G2)                          |
| `/api/v1/categories`   | `routers/v1/categories.py`   | `CategoriesService` — CRUD, hierarchy, global seed read (G7)                     |
| `/api/v1/transactions` | `routers/v1/transactions.py` | `TransactionsService` — INCOME/EXPENSE CRUD + bulk (PPT-037 / #47)               |
| `/api/v1/movements`    | `routers/v1/movements.py`    | `TransactionsService` — TRANSFER alias (PPT-037 / #47)                           |
| `/api/v1/reports`      | `routers/v1/reports.py`      | `ReportService` — spending/cash-flow/trends/export; budget-performance 501 (#48) |
| `/api/v1/health`       | `routers/v1/health.py`       | `probe_database` + Auth + optional Redis readiness (`/redis`)                    |

Schemas: `schemas/accounts.py`, `schemas/categories.py`, `schemas/transactions.py`, `schemas/movements.py`,
`schemas/reports.py`, `schemas/query_params.py`; enum slugs via `schemas/converters.py`.

All public modules under `modules/api/src/papita_txnsapi/` carry Google-style docstrings (routers, dependencies, schemas, core).

Live API integration: `modules/api/tests/test_accounts_categories_live_db.py`, `test_reports_live_db.py` (`@requires_postgres` B0);
`test_supabase_b1_smoke.py` (`@requires_supabase_b1` pooler `:6543`, includes reports spending probe).

## Invariants

- All DB models use schema `papita_transactions` via `BaseSQLModel`.
- PostgreSQL only (B0 Docker local, B1 Supabase hosted). DuckDB deprecated.
- Soft deletes by default; repositories use `@SQLDatabaseConnector.connect`.
- `OwnedTableDTO` services require `owner=UsersDTO` (`BaseService._ensure_owner`).
- Report aggregations require `owner=` on every `ReportService` public method; optional `account_id` must belong to that tenant.
- Categories: unique `(owner_id, name, category_kind)` with `NULLS NOT DISTINCT` (FR-15).

## Specs

| Topic                  | File                                                                   |
| ---------------------- | ---------------------------------------------------------------------- |
| PPT-031 design program | `docs/design/README.md`                                                |
| v3 migration runbook   | `docs/design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34` |
| Auth contract          | `docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`   |
| API ↔ model mapping    | `docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33` |
| Module-level detail    | `architecture/<slug>.md` (add as subsystems stabilize)                 |

## The docs tree (grow on demand)

`product/` PRDs · `architecture/` specs · `decisions/` ADRs · `reference/` stable facts · `ops/` procedures (+ `incidents/`, `release-rollback.md`) · `CHANGELOG.md` at first release · `roadmap.md` only if strategic themes need a home. Folders exist; files appear when content does.
