---
name: save-ma-money State
description: v3 model — balance reports, partitioning, config package, migration squash (2026-07-07).
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-10.** PPT-036 ([#46](https://github.com/Elmorralito/save-ma-money/issues/46)) accounts + categories CRUD implemented in API layer.

### Last completed

- **PPT-036 / #46:** 11 endpoints — `routers/v1/accounts.py`, `routers/v1/categories.py`; Pydantic schemas; mocked route tests; live-DB CRUD tests (`@requires_postgres`); G8 `initial_value` balance fallback in API responses; model-layer fixes (owned-repo owner passthrough, category `to_dao`, soft-delete flatten).
- **CI quality-control:** push-to-`main` trigger, Postgres 15 service, Alembic migrate before pytest; `postgres_gate.py` skips live tests when DB unreachable.
- **PPT-035 / #44:** auth routes + tenant context; merged PR [#82](https://github.com/Elmorralito/save-ma-money/pull/82).
- **PPT-033 / #43:** merged [PR #80](https://github.com/Elmorralito/save-ma-money/pull/80) — coverage matrix published.
- v3 schema squash: Alembic head `g4b5c6d7e8f9` (seed → period-balance MVs → MV fetch indexes → table indexes → **monthly transaction partitioning**).
- Balance reports: YAML registry `config/data/balance_report_filters.yaml`, `BalanceReportsService` / `BalanceReportsHandler`, unified repository + filter validation.
- Tests: model + API pytest green; B1 smoke gated on Supabase pooler URL (`test_supabase_b1_smoke.py`).

### Next action

- Open PR for PPT-036 (omit `docs/coverage.xml` from commit); CI quality-control runs B0 live tests via Postgres service + `@requires_postgres`.
- B1 Supabase smoke (`test_supabase_b1_smoke.py`) runs only when `DATABASE_URL` targets pooler `:6543` — manual / scheduled, not default CI.
- Start PPT-037 ([#47](https://github.com/Elmorralito/save-ma-money/issues/47)) — transactions + movements routers (opening-balance ledger txn).

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` / `modules/api/src/.env` for integration work.

### Uncommitted / staging notes

- **Strata pre-commit:** strict pairing requires `.strata/` (or `AGENTS.md` / `CLAUDE.md`) staged whenever `modules/**` or `deploy/**` change; strict mode also runs Python/Bash review via `strata_code_review.sh`.
