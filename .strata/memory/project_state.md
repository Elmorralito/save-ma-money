---
name: save-ma-money State
description: v3 model — balance reports, partitioning, config package, migration squash (2026-07-07).
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-07.** PR [#53](https://github.com/Elmorralito/save-ma-money/pull/53) on `refactor/PPT-031e` — CI fixes pushed (PyJWT swap, pre-commit formatting).

### Last completed

- v3 schema squash: Alembic head `g4b5c6d7e8f9` (seed → period-balance MVs → MV fetch indexes → table indexes → **monthly transaction partitioning**).
- Balance reports: YAML registry `config/data/balance_report_filters.yaml`, `BalanceReportsService` / `BalanceReportsHandler`, unified repository + filter validation.
- CI babysit (PR #53): `python-jose` → `PyJWT`; pre-commit formatting; MV SQL test assertions aligned with SQLFluff join order.
- Config package: `config/data/` (YAML), `config/transaction_partitions.py`, `config/materialized_views.py`; retired `configs/` package (logger YAML moved).
- MV layer: five balance-report MVs + `views/indexes.py` fetch-support indexes; event-driven refresh via `balance_views.py`.
- Deploy: `deploy/transaction_partitions.sh` (10-year retention, monthly ensure/archive); `deploy/alembic.sh` Poetry/venv fix.
- Tests: **335** model tests passing; pre-commit shellcheck/flake8/pylint/mypy green after lint fixes.
- Strata: `.strata/docs/ARCHITECTURE.md` updated for config paths, partitioning, balance reports.

### Next action

- Merge PR #53 after CI green; maintainer G1 sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28).
- API #25 remains out of scope.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` / `modules/api/src/.env` for integration work.

### Uncommitted / staging notes

- Large staged diff spans `modules/**`, `deploy/**`, `.strata/**`, and design runbook docs.
- **Strata pre-commit:** strict pairing requires `.strata/` (or `AGENTS.md` / `CLAUDE.md`) staged whenever `modules/**` or `deploy/**` change.
- CI Strata Check compares **committed** `origin/base...HEAD`; run `strata_check.sh` locally before push if commits were split.
