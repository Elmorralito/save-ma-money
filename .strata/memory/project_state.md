---
name: save-ma-money State
description: v3 model — balance reports, partitioning, config package, migration squash (2026-07-07).
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-10.** PPT-035 auth hardening (local): rate limits, JWT `type` check, inactive-user guard, Argon2 rehash-on-login.

### Last completed

- **PPT-035 hardening (local):** auth rate limits, JWT `type` validation, inactive/soft-deleted rejection on `/me`, Argon2 rehash on login.
- **PPT-035 / #44:** auth routes + tenant context; PR [#82](https://github.com/Elmorralito/save-ma-money/pull/82).
- **PPT-033 / #43:** merged [PR #80](https://github.com/Elmorralito/save-ma-money/pull/80) — coverage matrix published.
- v3 schema squash: Alembic head `g4b5c6d7e8f9` (seed → period-balance MVs → MV fetch indexes → table indexes → **monthly transaction partitioning**).
- Balance reports: YAML registry `config/data/balance_report_filters.yaml`, `BalanceReportsService` / `BalanceReportsHandler`, unified repository + filter validation.
- CI babysit (PR #53): `python-jose` → `PyJWT`; pre-commit formatting; MV SQL test assertions aligned with SQLFluff join order.
- Config package: `config/data/` (YAML), `config/transaction_partitions.py`, `config/materialized_views.py`; retired `configs/` package (logger YAML moved).
- MV layer: five balance-report MVs + `views/indexes.py` fetch-support indexes; event-driven refresh via `balance_views.py`.
- Deploy: `deploy/transaction_partitions.sh` (10-year retention, monthly ensure/archive); `deploy/alembic.sh` Poetry/venv fix.
- Tests: **335** model tests passing; pre-commit shellcheck/flake8/pylint/mypy green after lint fixes.
- Strata: `.strata/docs/ARCHITECTURE.md` updated for config paths, partitioning, balance reports.

### Next action

- Merge PR #82; rebuild Docker API for `/auth/*` on `:8000`.
- Start PPT-036 ([#46](https://github.com/Elmorralito/save-ma-money/issues/46)) — accounts + categories routers using `get_current_owner`.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` / `modules/api/src/.env` for integration work.

### Uncommitted / staging notes

- **Strata pre-commit:** strict pairing requires `.strata/` (or `AGENTS.md` / `CLAUDE.md`) staged whenever `modules/**` or `deploy/**` change; strict mode also runs Python/Bash review via `strata_code_review.sh`.
