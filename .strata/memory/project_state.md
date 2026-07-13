---
name: save-ma-money State
description: PPT-038 reports API wired on feat/PPT-038; health DB probe + PPT-044 brief staged.
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** PPT-038 ([#48](https://github.com/Elmorralito/save-ma-money/issues/48)) on `feat/PPT-038`
— tenant-scoped `/reports/*` wired to `ReportService`; G9 cash-flow MV refresh; pylint pre-commit fixes applied
(`export_format` alias, locals extraction). Also staged: structured `/health/database` probe + PPT-044 brief.

### Last completed (this session)

- **PPT-038 / #48:** `routers/v1/reports.py`, `schemas/reports.py`, report query deps; `ReportService` owner guards +
  `account_id` ownership via `AccountsService`; JWT on all report routes including budget-performance 501; unit + B0/B1
  probe tests; Google-style docs on transactions/movements/reports routers.
- **Health:** `probe_database` with allowlisted details + latency; `GET /health/database`.
- **Docs:** `docs/issues/PPT-044-api-hardening-brief.md` (#89); issue title conventions prefer Conventional Commit types.

### Next action

- Re-run pre-commit / commit PPT-038 (omit `docs/coverage.xml`).
- Close or verify #48 after push; pick PPT-040 (#50) CI dual-target or PPT-044 (#89) hardening.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d`
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` for B0 live report tests; pooler `:6543` for B1 smoke.

### Uncommitted / staging notes

- Stage `.strata/` with `modules/**` (strict pairing).
- Prefer dropping `docs/coverage.xml` from the commit.
- Split commits optional: reports vs health probe vs PPT-044 docs.
