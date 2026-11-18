---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

**Strata issues policy:** do **not** keep closed GitHub issues under `.strata/issues/`
(including `archive/`) — they add agent context noise. History lives on GitHub / git.
Capture with `/strata:capture` only for work in flight.

### Last completed (this session)

- **PPT-096 (Phase 0 of #261 / PPT-095):** Pruned dead v0 access stubs (`assets`, `indexers`, `liabilities`, `types`), DuckDB remnants (`setup_duckdb.py`, `AlembicDuckDBImpl`, `DuckDBUpserter`, connector DuckDB fallbacks), registrar-era `papita_txnsmodel/handlers/` (~1,910 LOC), and API/Web placeholders (`budgets.py`, `split_transaction`, `budget-performance`, `broker.py`, `api_tier.py`, `StubPage.tsx`, `client_contract.py` header bloat); regenerated OpenAPI types (`openapi.json` + `api.d.ts`).

### In progress (ACTIVE)

- **PPT-095 / #261:** Vertical-slice baseline reset (`backend/` + `modules/web/`).
  - Canonical Auth Prerequisite Gate locked: **Stateless JWKS Bearer** (Supabase Auth JWTs + local HS256 for B0 tests; remove BFF cookie/session store in `PPT-100`).
  - Next phase: **PPT-097 (Phase 1)** — Standardize SQLAlchemy `Session` DI (`Depends(get_db)` / `session_scope()`), flatten `TableDTO` / `extends.py` / `BalanceReports`, add `Accounts.include_in_balance`, and converge `model` + `api` into `backend/`.

### Open (backlog)

- **PPT-097 (Phase 1):** Session DI, flatten layers, converge `model` + `api` into `backend/`.
- **PPT-098 (Phase 2A):** Merge `ingestor-core` + `ingestors/email` into `backend/domains/ingestion/` (drop Prefect & registries).
- **PPT-099 (Phase 2B):** Unify `/transactions` + `/movements` API & SPA ledger screens + `settlement_status` (`settled` | `in_transit`).
- **PPT-100 (Phase 3):** Consolidate auth to stateless JWKS Bearer; replace 6 Python linters with `ruff`; prune `bin/` and CI workflows.

### Next action

- Execute **PPT-097 (Phase 1)** on top of the clean Phase 0 baseline.
