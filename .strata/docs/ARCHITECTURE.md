# Architecture — save-ma-money

The codemap: where things happen, coarse module by coarse module — a map of a country, not an atlas. Keep it concise; name modules and invariants; avoid deep links that go stale (use search). Detail lives in `architecture/<slug>.md`, indexed below.

## Map

- **`modules/model`** — `papita_txnsmodel`: SQLModel tables under `src/papita_txnsmodel/model/`, DTOs/repositories in `access/`, business logic in `services/`, loaders in `handlers/`. Alembic under `alembic/`.
- **`modules/api`** — `papita_txnsapi`: FastAPI app scaffold; `core/settings.py`, `core/security.py` (JWT). Target routes documented in `API_Endpoints.md.md`.
- **`deploy/`** — shared shell utilities, `alembic.sh`, `test.sh`.
- **`docker/database/`** — local PostgreSQL 15 via Compose for dev and migration CI.

Registrar package is referenced in pytest config but not present in the tree yet.

## Invariants

- All DB models use schema `papita_transactions` via `BaseSQLModel`.
- PostgreSQL is the target database; DuckDB is deprecated (see `docs/issues/PPT-031-C-supabase-decision-brief.md`).
- Soft deletes by default; repositories use `@SQLDatabaseConnector.connect`.

## Specs

| Topic                  | File                                                   |
| ---------------------- | ------------------------------------------------------ |
| PPT-031 design program | `docs/design/README.md`                                |
| Auth contract          | `docs/design/PPT-031-auth-contract.md`                 |
| API ↔ model mapping    | `docs/design/PPT-031-api-model-mapping.md`             |
| Module-level detail    | `architecture/<slug>.md` (add as subsystems stabilize) |

## The docs tree (grow on demand)

`product/` PRDs · `architecture/` specs · `decisions/` ADRs · `reference/` stable facts · `ops/` procedures (+ `incidents/`, `release-rollback.md`) · `CHANGELOG.md` at first release · `roadmap.md` only if strategic themes need a home. Folders exist; files appear when content does.
