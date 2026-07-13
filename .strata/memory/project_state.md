---
name: save-ma-money State
description: PPT-037 transactions + movements API in progress on feat/PPT-037.
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** PPT-037 ([#47](https://github.com/Elmorralito/save-ma-money/issues/47)) on `feat/PPT-037`
— transactions + movements CRUD wired to `TransactionsService`; pre-commit lint fixes in flight.

### Last completed

- **PPT-037 (in progress):** `/transactions` and `/movements` routers, schemas, query-param dependencies,
  model-layer `TransactionListFilterSpec`, SQL pagination/count in `BaseRepository`, `AccountBalances` ORM view.
- **PPT-036 / #46 (merged):** PR [#84](https://github.com/Elmorralito/save-ma-money/pull/84) — accounts + categories.
- **Pre-commit patterns:** bundled list filters via `Depends(get_*_list_query)`, TypedDict service kwargs, pylint
  disables only where filter arity exceeds limits.

### Next action

- Pass local pre-commit (`flake8`, `pylint`, `mypy`, `strata-validate`) and commit PPT-037.
- Omit regenerated artifacts: `docs/coverage.xml`, `docs/interrogate_badge.svg`.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` / `modules/api/src/.env` for integration work.

### Uncommitted / staging notes

- Stage `.strata/memory/project_state.md` with `modules/**` changes before commit (strict pairing).
- `matching.py` handler docs updated in a separate pass.
