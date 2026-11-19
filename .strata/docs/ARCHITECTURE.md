# Architecture — save-ma-money

The codemap after the **PPT-095 (`#261`) vertical-slice reset**:

## Map

- **`modules/backend/`** (`papita-backend`) — single deployable Python package (with self-contained `Dockerfile`) containing:
  - **`modules/backend/core/`** (`src/backend/core/`) — `Settings`, `DatabaseSessionManager` (`configure_database`, `get_db`, `session_scope`, `with_session`), `AuthSecurityManager`, and `get_current_owner`.
  - **`modules/backend/domains/`** (`src/backend/domains/`) — vertical domain slices:
    - `accounts/` — `Accounts` (with `include_in_balance: bool = True` and `currency: CHAR(3)`), 1:1 account extension tables, `AccountsDTO`, `AccountsRepository`, `AccountsService`, and `/api/v1/accounts` router.
    - `categories/` — `Categories`, `CategoriesDTO`, `CategoriesRepository`, `CategoriesService`, and `/api/v1/categories` router.
    - `transactions/` — unified ledger for `INCOME`, `EXPENSE`, and `TRANSFER` (`Transactions` with `currency: CHAR(3)`, `template_id`, and `settlement_status: SettlementStatus`), `TransactionTemplates`, `TransactionsService`, and `/api/v1/transactions` (+ `/api/v1/transactions/{id}/execute`) and `/api/v1/transaction-templates` routers.
    - `reports/` — `ReportService`, balance materialized views (`account_balances`, `owner_*_balances`), and `/api/v1/reports` router.
    - `ingestion/` — `TransactionIngestionProvenance`, `IngestionDeadLetter`, `IngestionConnection`, `IngestionRun`, `IngestionBridgeService`, `IngestionRunner`, `BancolombiaParser` / `NequiParser` / `FallbackEmailParser`, `GmailSource`, CLI (`python -m backend.domains.ingestion.cli --once`), and `/api/v1/ingestion` router.
    - `auth/` — `Users`, `UsersService`, and stateless Bearer JWT `/api/v1/auth` router.
  - **`backend/alembic/`** — PostgreSQL migrations.
- **`modules/web/`** (`@papita/web`) — Vite + React 19 + TypeScript SPA. Presentation-only; uses OpenAPI generated types (`openapi/openapi.json` → `src/types/api.d.ts`), TanStack Query, and in-memory stateless Bearer authentication against `/api/v1/auth/*`.

## Invariants

- All DB models use schema `papita_transactions` via `BaseSQLModel`.
- PostgreSQL only (zero DuckDB code or scripts).
- Standard SQLAlchemy `Engine` + `sessionmaker` (`DatabaseSessionManager` + `Depends(get_db)` / `@with_session`).
- Guardrails (`#261`):
  - `Accounts.include_in_balance` separates account lifecycle (`active`) from net-worth/balance inclusion.
  - `currency: CHAR(3)` is preserved on `Accounts` and `Transactions`.
  - `template_id` is preserved on `Transactions` for Planned-vs-Actual variance.
  - `settlement_status` (`settled` | `in_transit`) is persisted on `Transactions` for transit-aware transfers (`PPT-101`).
- Python quality gate: `ruff` (`ruff check` + `ruff format`) + `mypy` + `pytest`.
