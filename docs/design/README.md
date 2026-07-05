# PPT-031 Design Documents

Design artifacts for [refactor(PPT-031): Simplify #28](https://github.com/Elmorralito/save-ma-money/issues/28).

## Document ↔ issue map

| Document | Issue | Description |
|----------|-------|-------------|
| [`../issues/PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md) | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) | Parent requirements (FR/NFR, tracks A–F) |
| [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md) | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) | As-is schema audit (3NF, handlers, API gaps) |
| [`../issues/PPT-031-C-supabase-decision-brief.md`](../issues/PPT-031-C-supabase-decision-brief.md) | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) | Supabase × FastAPI decision (B0–B3) |
| `PPT-031-v1-schema.md` *(planned)* | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) | Target schema v1–v3 + ER diagram |
| `PPT-031-api-model-mapping.md` *(planned)* | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) | Endpoint → DTO → SQLModel mapping |
| `PPT-031-migration-runbook.md` *(planned)* | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) | Alembic + Supabase PostgreSQL validation |
| `PPT-031-auth-contract.md` *(planned)* | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E | Auth/register/login/JWT (FR-10, FR-11) |

## Platform

**PostgreSQL via Supabase** — DuckDB is out of scope ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)).
