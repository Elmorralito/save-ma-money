---
name: save-ma-money State
description: v3 model — balance reports, partitioning, config package, migration squash (2026-07-07).
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-09.** PPT-033 ([#43](https://github.com/Elmorralito/save-ma-money/issues/43)) — API spec validated against v3 model; coverage matrix published.

### Last completed

- **PPT-033 / #43:** [`docs/design/PPT-033-api-coverage-matrix.md`](../../docs/design/PPT-033-api-coverage-matrix.md) — 32 MVP endpoints mapped to model services; doc drift fixes in mapping doc + API README cross-links.
- v3 schema squash: Alembic head `g4b5c6d7e8f9` (seed → period-balance MVs → MV fetch indexes → table indexes → **monthly transaction partitioning**).
- Balance reports: YAML registry `config/data/balance_report_filters.yaml`, `BalanceReportsService` / `BalanceReportsHandler`, unified repository + filter validation.
- CI babysit (PR #53): `python-jose` → `PyJWT`; pre-commit formatting; MV SQL test assertions aligned with SQLFluff join order.
- Config package: `config/data/` (YAML), `config/transaction_partitions.py`, `config/materialized_views.py`; retired `configs/` package (logger YAML moved).
- MV layer: five balance-report MVs + `views/indexes.py` fetch-support indexes; event-driven refresh via `balance_views.py`.
- Deploy: `deploy/transaction_partitions.sh` (10-year retention, monthly ensure/archive); `deploy/alembic.sh` Poetry/venv fix.
- Tests: **335** model tests passing; pre-commit shellcheck/flake8/pylint/mypy green after lint fixes.
- Strata: `.strata/docs/ARCHITECTURE.md` updated for config paths, partitioning, balance reports.

### Next action

- Merge PPT-033 PR (coverage matrix + doc alignment) and close [#43](https://github.com/Elmorralito/save-ma-money/issues/43).
- Start PPT-034 ([#45](https://github.com/Elmorralito/save-ma-money/issues/45)) — FastAPI scaffold + health on B0 Docker Postgres.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` / `modules/api/src/.env` for integration work.

### Uncommitted / staging notes

- Large staged diff spans `modules/**`, `deploy/**`, `.strata/**`, and design runbook docs.
- **Strata pre-commit:** strict pairing requires `.strata/` (or `AGENTS.md` / `CLAUDE.md`) staged whenever `modules/**` or `deploy/**` change.
- CI Strata Check compares **committed** `origin/base...HEAD`; run `strata_check.sh` locally before push if commits were split.
