---
name: save-ma-money State
description: PPT-038 PR #90; linked txn services + report DAO flatten CI fix pushed.
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** PPT-038 ([#48](https://github.com/Elmorralito/save-ma-money/issues/48)) on
[PR #90](https://github.com/Elmorralito/save-ma-money/pull/90) (`feat/PPT-038`). B0 live report seed failed in
`quality-control` until transaction link services were wired and report frames flattened from DAO columns.

### Last completed (this session)

- **CI fix:** `get_transactions_service` calls `load_link_services` (accounts/categories/templates);
  `LinkedEntitiesService.create` skips `None` FKs; `ReportService._load_transactions` flattens single-column DAO
  frames and timezone-safe date windows.
- **PPT-038:** tenant-scoped `/reports/*`, G9 cash-flow MV refresh, structured `/health/database`, PPT-044 brief.

### Next action

- Watch PR #90 `quality-control` green; merge when mergeable.
- Then PPT-040 (#50) CI dual-target or PPT-044 (#89) hardening.

### Prerequisites

- Local Postgres: `docker compose -f docker/database/docker-compose.yml up -d` (host port often `5435`)
- Migrations: `./deploy/alembic.sh upgrade --docker-rm`
- `DATABASE_URL` for B0 live report tests; pooler `:6543` for B1 smoke.

### Uncommitted / staging notes

- Stage `.strata/` with `modules/**` (strict pairing).
- Prefer dropping `docs/coverage.xml` from the commit.
