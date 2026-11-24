---
name: save-ma-money State
description: Vertical-slice baseline reset (PPT-095 / #261) completed across Phases 0–3.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** keep **user management and authentication in the Supabase
project** using stateless JWKS Bearer tokens (`/api/v1/auth/*`). Papita API verifies
JWTs and links `users` by `sub`.

### Last completed (this session)

- **Self-hosted single-owner AI sidecar (`feat/self-hosted-ai-agent-sidecar`):**
  - Added optional Compose profile `ai-agent` (`backend.domains.ai_agent.{adapters,app}`) with `AIAgentRegistry` supporting simultaneous API (`ollama`, `openai_compat`) and headless CLI (`cli:claude`, `cli:agy`, `cli:cursor`) connections, scrubbed subprocess env (`shell=False`, no tools), constant-time `X-Papita-AI-Secret`, and SSE streaming.
  - Exposed `/api/v1/ai/{status,chat,chat/stream}` in `papita_txnsapi` with fail-closed single-owner lock (`AI_AGENT_ENABLED` + `AI_AGENT_ALLOWED_OWNER_ID`), rate limiting, and redacted aggregated financial-health context; added nginx SSE location (`proxy_buffering off`) and synced `openapi.json` + `api.d.ts`.
- **Per-user email ingestion channel config & privacy hardening (`feat/email-ingestion-channel-config`):**
  - Added Alembic migration `q4f5a6b7c8d9` adding `email_senders`, `email_subjects`, `email_source_label`, and `email_query` to `papita_transactions.ingestion_connections` and exposed owner-scoped `PUT /api/v1/ingestion/connections`, `PATCH /api/v1/ingestion/connections/{connection_id}`, and `DELETE /api/v1/ingestion/connections/{connection_id}` (strict sender/subject/label/lookback validation, no raw `email_query` on public API, allowlisted `provider`/`flow_name`).
  - Extended `build_gmail_query()` (multi-sender/subject `OR` clauses, `source_label`, parenthesized raw `q`), wired `email_flow.py` to load per-user DB connection settings (honoring `enabled=False`, failing closed when no channel filters are configured, and preserving existing DB config on worker status upserts), and redacted email DLQ payloads + sanitized logs/`error_summary`.
  - Synced `modules/web/openapi/openapi.json` and `modules/web/src/types/api.d.ts`.
- **Plugin-based connector & parser architecture (`feat/plugin-connector-architecture`):**
  - Added `PluginManifest`, `BaseBatchImporter`, thread-safe `ConnectorRegistry` (Python `importlib.metadata.entry_points` + explicit registration, manifest caching, `PAPITA_INGESTOR_ENABLED_PLUGINS` allowlist), `IngestorPluginError`/`IngestorRateLimitError`, `parse_many()`, and promoted provider-agnostic `run_status.py`/`status_mapping.py` into `papita_ingestor_core`.
  - Declared `papita.ingestor.{sources,parsers,importers}` entry points in `modules/backend/pyproject.toml`; decoupled `GmailSource`, email parsers (`bancolombia-email`, `global66-email`, `nequi-email`, `fallback-email`), and `email_flow.py` (`--connector <id>` + registry lookup).
  - Extracted provider-agnostic `PortfolioImportService` / `NormalizedPortfolioBatch` in `papita_txnsmodel/services/portfolio_import.py` (zero `papita_ingestor_*` imports), added `IBKRStatementImporter` (`ibkr-activity-csv`), and exposed `GET /api/v1/ingestion/connectors` + `POST /api/v1/ingestion/statements/{importer_id}` (synced `openapi.json` + `api.d.ts`).
  - Added sibling `AuthProvider` protocol (`papita_txnsapi/core/auth_provider.py`, `register_auth_provider`, `get_auth_provider`) and wired `routers/v1/health.py` through it.
- **PPT-101 (`#262`) IBKR Activity Statement + Global66 Wire Import, FX Valuation, and In-Transit Settlement:**
  - Added Alembic migration `p3e4f5a6b7c8` adding `accounts.fx_rate`, widening `trading_account_details.units` to `DECIMAL(22,8)`, adding `symbol`/`unit_price`/`fx_rate`/`unrealized_pnl` to `trading_account_details`, and updating `account_balances.sql` to filter `settlement_status = 'SETTLED'` so in-transit transfers do not distort reconciled balances.
  - Added `Global66Parser` (`papita_ingestor_email/parsers/global66.py`, registered in `default_email_parsers()`) emitting `TRANSFER` records with `settlement_status = IN_TRANSIT` (or `SETTLED`), wired `settlement_status` through `ParsedRecord` → `to_ingest_transaction_request`, and exposed `POST /api/v1/transactions/{transaction_id}/settle`.
  - Added multi-section IBKR Activity Statement CSV parser (`papita_ingestor_core/importers/ibkr.py`), idempotent `IBKRImportService` (`papita_txnsmodel/services/ibkr_import.py`), and `POST /api/v1/ingestion/ibkr/activity-statement` computing `units * unit_price * fx_rate`, linking `AccountFinancing` for Margin LTV, and ingesting settled deposits via `(owner_id, CSV, source_ref)`.
  - Wired `trading_details_by_id` into `ReportService.financial_health` / `compute_financial_health` and regenerated `modules/web/openapi/openapi.json` + `modules/web/src/types/api.d.ts`.
- **PPT-088 (`#181`) Automation-first Home (Financial Health Scorecard & Live Pulse):**
  - Added pure model scorecard helper (`report_health.py`) + `ReportService.financial_health` and exposed `GET /api/v1/reports/financial-health` (Redis cached) computing Reconciled Net Worth (active & `include_in_balance` Assets − Liabilities), Liquid Cash Runway, Monthly Contractual Debt Service, Monthly Interest Drag, Debt-to-Asset ratio, and collateralized Margin LTV from `account_financing`.
  - Added optional `settlement_status` filter on `GET /api/v1/transactions` (`query_filters.py`, `TransactionsService.list_transactions`, `TransactionListQuery`) and synced OpenAPI (`openapi.json` + `api.d.ts`).
  - Added thin Web ingestion client (`src/api/ingestion.ts`, graceful 404 → `null` on `/runs/latest`), `getFinancialHealthReport`, and upgraded `DashboardPage` with `FinancialHealthScorecard` (including multi-currency switcher aligned with Operating Free Cashflow), `LivePulseSection` (ingestion status + monthly Operating FCF), and `In-transit transfers` panel with zero TS domain math.
  - Added Playwright E2E assertions in `modules/web/e2e/critical-path.spec.ts` verifying Financial Health Scorecard, Ingestion status, Operating Free Cashflow, In-transit transfers, and Due soon sections on `/dashboard`.
- **PPT-091 (`#184`) Operating Free Cashflow Waterfall, Planned-vs-Actual Variance & Debt Paydown Simulator:**
  - Added `CashflowBucket` enum + nullable `categories.cashflow_bucket` and `credit_card_account_details.cashflow_only` (`o2d3e4f5a6b7` Alembic migration, DTOs, API CRUD schemas, and category/account SPA form controls).
  - Implemented pure model analytics (`report_common.py`, `report_waterfall.py`, `report_variance.py`, `report_debt.py`) wired into `ReportService` and exposed `GET /api/v1/reports/operating-cashflow`, `GET /api/v1/reports/planned-vs-actual`, `GET /api/v1/reports/debt-paydown` (Redis cached), and `POST /api/v1/reports/debt-paydown/simulate` (rate-limited).
  - Upgraded `ReportsPage` with a 4-KPI semantic strip, 4 URL-synced ARIA tabs (`Operating Cashflow`, `Planned vs. Actual`, `Debt Paydown`, `Spending`), accessible SVG/CSS visuals, zero TS domain math, single-currency scoping warning, and `queryKeys.reports.all` cache invalidation across ledger/template/account/category mutations.
- **PPT-100 (Phase 3 of #261 / PPT-095):** Consolidated authentication to stateless JWKS Bearer (`/api/v1/auth/*`, removing BFF cookie/session store `bff_auth.py`, `bff_session.py`, `session_store.py`, `bff_csrf.py`, and SPA CSRF); replaced 6 Python linters (`black`, `isort`, `flake8`, `pylint`, `interrogate`, `ci-adoption-check`) with `ruff` + `mypy` + `pytest`; pruned redundant `bin/bash/` and `.github/scripts/` helpers and consolidated `.github/workflows/`.
- **PPT-099 (Phase 2B of #261 / PPT-095):** Added `SettlementStatus` (`SETTLED` | `IN_TRANSIT`) to `Transactions` (`n1c2d3e4f5a6` migration + DTO + schemas); unified `/movements` into `/transactions` (supporting `income`, `expense`, `transfer`, `from_account_id`/`to_account_id`, `settlement_status`, `template_id`, and `POST /api/v1/transactions/{id}/execute`); folded `MovementsPage` into `TransactionsPage` and redirected `/movements` → `/transactions`.
- **PPT-098 (Phase 2A of #261 / PPT-095):** Merged `modules/ingestor-core` and `modules/ingestors/email` into `backend/domains/ingestion/` (`backend/src/papita_ingestor_*`), removed Prefect `@flow` wrapper and `ParserRegistry`/`SourceRegistry` indirection in favor of explicit parser lists (`select_parser`, `default_email_parsers()`) and CLI `python -m backend.domains.ingestion.cli --once`, and wired optional `source_ref` on `POST /api/v1/transactions` to share `IngestionBridgeService`.
- **PPT-097 (Phase 1 of #261 / PPT-095):** Replaced `SQLDatabaseConnector` with `DatabaseSessionManager` (`Depends(get_db)`, `session_scope()`, `@with_session`); removed `services/extends.py` and `balance_reports/`; added `Accounts.include_in_balance` (`m0b1c2d3e4f5`); retired PyPI model release workflows; converged `modules/model` and `modules/api` into `backend/`.
- **PPT-096 (Phase 0 of #261 / PPT-095):** Pruned dead v0 stubs, DuckDB remnants, registrar-era `handlers/`, and API/Web placeholders.

### Next action

- Commit/PR **PPT-101 (`#262`)** on branch `262-featppt-101-...` and validate migration upgrade/downgrade on Docker Postgres; optionally file an issue for **Agent/MCP readiness** (`papita-mcp` + compact snapshot endpoint + PAT auth).
