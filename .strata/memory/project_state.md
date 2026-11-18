---
name: save-ma-money State
description: Vertical-slice baseline reset (PPT-095 / #261) completed across Phases 0–3.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** keep **user management and authentication in the Supabase
project** using stateless JWKS Bearer tokens (`/api/v1/auth/*`). Papita API verifies
JWTs and links `users` by `sub`.

### Last completed (this session)

- **PPT-100 (Phase 3 of #261 / PPT-095):** Consolidated authentication to stateless JWKS Bearer (`/api/v1/auth/*`, removing BFF cookie/session store `bff_auth.py`, `bff_session.py`, `session_store.py`, `bff_csrf.py`, and SPA CSRF); replaced 6 Python linters (`black`, `isort`, `flake8`, `pylint`, `interrogate`, `ci-adoption-check`) with `ruff` + `mypy` + `pytest`; pruned redundant `bin/bash/` and `.github/scripts/` helpers and consolidated `.github/workflows/`.
- **PPT-099 (Phase 2B of #261 / PPT-095):** Added `SettlementStatus` (`SETTLED` | `IN_TRANSIT`) to `Transactions` (`n1c2d3e4f5a6` migration + DTO + schemas); unified `/movements` into `/transactions` (supporting `income`, `expense`, `transfer`, `from_account_id`/`to_account_id`, `settlement_status`, `template_id`, and `POST /api/v1/transactions/{id}/execute`); folded `MovementsPage` into `TransactionsPage` and redirected `/movements` → `/transactions`.
- **PPT-098 (Phase 2A of #261 / PPT-095):** Merged `modules/ingestor-core` and `modules/ingestors/email` into `backend/domains/ingestion/` (`backend/src/papita_ingestor_*`), removed Prefect `@flow` wrapper and `ParserRegistry`/`SourceRegistry` indirection in favor of explicit parser lists (`select_parser`, `default_email_parsers()`) and CLI `python -m backend.domains.ingestion.cli --once`, and wired optional `source_ref` on `POST /api/v1/transactions` to share `IngestionBridgeService`.
- **PPT-097 (Phase 1 of #261 / PPT-095):** Replaced `SQLDatabaseConnector` with `DatabaseSessionManager` (`Depends(get_db)`, `session_scope()`, `@with_session`); removed `services/extends.py` and `balance_reports/`; added `Accounts.include_in_balance` (`m0b1c2d3e4f5`); retired PyPI model release workflows; converged `modules/model` and `modules/api` into `backend/`.
- **PPT-096 (Phase 0 of #261 / PPT-095):** Pruned dead v0 stubs, DuckDB remnants, registrar-era `handlers/`, and API/Web placeholders.

### Next action

- All phases of Epic **PPT-095 (`#261`)** (`PPT-096` through `PPT-100`) are complete and verified. Ready for downstream **PPT-101 (`#262`)**.
