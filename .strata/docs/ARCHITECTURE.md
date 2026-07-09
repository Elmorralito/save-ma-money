# Architecture — save-ma-money

The codemap: where things happen, coarse module by coarse module — a map of a country, not an atlas. Keep it concise; name modules and invariants; avoid deep links that go stale (use search). Detail lives in `architecture/<slug>.md`, indexed below.

## Map

- **`modules/model`** — `papita_txnsmodel`: SQLModel tables under `src/papita_txnsmodel/model/` (composite indexes on `accounts`, `transactions`, `transaction_templates`, `account_financing`), DTOs/repositories in `access/`, business logic in `services/`, loaders in `handlers/`. Balance report MVs in `views/balance_reports/` (SQL + `views.py` entities); MV fetch indexes in `views/indexes.py`. Generic balance report reads: `config/data/balance_report_filters.yaml`, `config/balance_report_specs.py`, `access/balance_reports/`, `services/balance_reports.py`, `handlers/balance_reports.py`. Partition + MV registry: `config/transaction_partitions.py`, `config/materialized_views.py`. Alembic under `alembic/`.
- **`modules/api`** — `papita_txnsapi`: FastAPI app ([#45](https://github.com/Elmorralito/save-ma-money/issues/45)) — `main.py`, health probes, shared schemas/deps, budgets 501 stub; auth + domain routers in [#44](https://github.com/Elmorralito/save-ma-money/issues/44)–[#48](https://github.com/Elmorralito/save-ma-money/issues/48).
- **`deploy/`** — shared shell utilities, `alembic.sh`, `test.sh`, `transaction_partitions.sh` (monthly partition ensure + retention archive).
- **`docker/database/`** — local PostgreSQL 15 via Compose for dev and migration CI.

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

| Service                              | Module                      | Role                                                                                                |
| ------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------- |
| `AccountsService`                    | `services/accounts.py`      | CRUD + `create_account` / `update_account` extension orchestration by `account_kind`; `get_balance` |
| `TransactionsService`                | `services/transactions.py`  | CRUD + `list_transfers`, `create_transfer`, `complete_transfer`, `cancel`                           |
| `ReportService`                      | `services/reports.py`       | `spending`, `cash_flow`, `trends`, `export` (transaction SQL aggregations; FR-12)                   |
| `refresh_balance_materialized_views` | `services/balance_views.py` | Shared MV refresh helper (exported from `services/__init__.py`)                                     |

Extension routing map: `services/account_extension_routing.py`. Live-DB tenancy tests: `tests/tests_papita_txnsmodel/integration/` (require `DATABASE_URL` PostgreSQL).

## Invariants

- All DB models use schema `papita_transactions` via `BaseSQLModel`.
- PostgreSQL only (B0 Docker local, B1 Supabase hosted). DuckDB deprecated.
- Soft deletes by default; repositories use `@SQLDatabaseConnector.connect`.
- `OwnedTableDTO` services require `owner=UsersDTO` (`BaseService._ensure_owner`).
- Categories: unique `(owner_id, name, category_kind)` with `NULLS NOT DISTINCT` (FR-15).

## Specs

| Topic                  | File                                                   |
| ---------------------- | ------------------------------------------------------ |
| PPT-031 design program | `docs/design/README.md`                                |
| v3 migration runbook   | `docs/design/PPT-031-migration-runbook.md`             |
| Auth contract          | `docs/design/PPT-031-auth-contract.md`                 |
| API ↔ model mapping    | `docs/design/PPT-031-api-model-mapping.md`             |
| Module-level detail    | `architecture/<slug>.md` (add as subsystems stabilize) |

## The docs tree (grow on demand)

`product/` PRDs · `architecture/` specs · `decisions/` ADRs · `reference/` stable facts · `ops/` procedures (+ `incidents/`, `release-rollback.md`) · `CHANGELOG.md` at first release · `roadmap.md` only if strategic themes need a home. Folders exist; files appear when content does.
