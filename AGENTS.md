# save-ma-money — agent instructions

Before memory operations or deep project work, read [`.strata/MANIFEST.md`](.strata/MANIFEST.md) — the project memory contract (structure, routing rules, load order) — and load per its rules.

Project memory is repo-owned under `.strata/` (strata format, `layout_version: 3`). Do not write project memory to tool-owned paths such as `~/.codex/` or `~/.claude/`.

Keep memory rules out of this file — the manifest owns them. Operational content (build/test commands, code style, conventions, repo etiquette) belongs _here_.

---

## What this repo is

**save-ma-money** (also referred to as _save-ma-finances_ in README copy) is a Poetry monorepo for Papita financial transaction data: type-safe persistence, migrations, and a FastAPI REST surface.

| Goal            | Detail                                                                                                                                               |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary outcome | Auditable PostgreSQL-backed financial data with tested model layer and shippable API ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)) |
| Active packages | `papita-txnsmodel` (`modules/model`), `papita-txnsapi` (`modules/api`)                                                                               |
| Not in tree yet | `registrar` / `papita-txnsregistrar` (referenced in pytest paths only)                                                                               |
| Database        | **PostgreSQL only** — DuckDB is deprecated ([#31](https://github.com/Elmorralito/save-ma-money/issues/31))                                           |
| Auth direction  | Local JWT via `AuthSecurityManager` (B0/B1); Supabase deferred — see `docs/issues/PPT-031-C-supabase-decision-brief.md`                              |

---

## Repository map

```
save-ma-money/
├── pyproject.toml              # workspace root (package-mode = false)
├── modules/
│   ├── model/                  # papita-txnsmodel — primary implementation
│   │   ├── src/papita_txnsmodel/
│   │   │   ├── model/          # SQLModel tables (schema: papita_transactions)
│   │   │   ├── access/         # DTOs + repositories per domain
│   │   │   ├── services/       # business logic (BaseService)
│   │   │   ├── handlers/       # load/dump pipelines
│   │   │   └── database/       # SQLDatabaseConnector, upsert helpers
│   │   ├── alembic/            # migrations (alembic.ini in module root)
│   │   └── tests/
│   └── api/                    # papita-txnsapi — scaffold stage
│       └── src/papita_txnsapi/
│           ├── config/settings.py
│           └── core/security.py
├── deploy/                     # alembic.sh, test.sh, utils.sh
├── docker/database/            # local Postgres 15 Compose
├── docs/design/ · docs/issues/ # human design program (PPT-031)
├── .cursor/rules/gen-custom/   # enforced code style (Black 120, isort, mypy, pylint)
├── .strata/                    # agent memory (hot/warm/cold tiers)
└── .github/workflows/          # CI (quality, security, migrations, strata)
```

Domain entities in the model layer include **accounts**, **transactions**, **assets**, **liabilities**, **indexers**, **types**, and **users**.

---

## Layered architecture (model package)

Follow this stack for all database-backed features:

```
Model (SQLModel) → Access (DTO + Repository) → Service → Handler
```

| Layer      | Location                                    | Rules                                                                                         |
| ---------- | ------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Model      | `modules/model/src/papita_txnsmodel/model/` | Inherit `BaseSQLModel`; schema `papita_transactions`; soft delete via `active` + `deleted_at` |
| DTO        | `access/<domain>/dto.py`                    | Inherit `TableDTO`; implement `from_dao()` / `to_dao()`                                       |
| Repository | `access/<domain>/repository.py`             | Inherit `BaseRepository`; use `@SQLDatabaseConnector.connect`                                 |
| Service    | `services/<domain>.py`                      | Inherit `BaseService`; validate DTO types                                                     |
| Handler    | `handlers/`                                 | Inherit `AbstractLoadHandler` / `BaseLoadTableHandler` for ingest                             |

First-party import roots: `papita_txnsmodel`, `papita_txnsapi`, `papita_txnsregistrar` (when added).

---

## Environment and secrets

Never commit real secrets. Use templates only.

| File                           | Purpose                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| [`.env.example`](.env.example) | Root template — copy values to the paths below                     |
| `modules/api/src/.env`         | **Required** for API `Settings` (`JWT_SECRET_KEY`, `DATABASE_URL`) |
| `docker/database/.env`         | Docker Compose Postgres credentials                                |

Always set `DATABASE_URL` to a PostgreSQL URL. Omitting it can trigger legacy DuckDB fallback paths.

Local Postgres:

```bash
cp .env.example modules/api/src/.env   # edit JWT + DATABASE_URL
# optional: docker/database/.env for Compose
docker compose -f docker/database/docker-compose.yml up -d
```

---

## Setup, test, and quality

Python **3.12** recommended. Poetry **2.1.3** (matches CI).

```bash
# Install workspace (path deps: model + api)
poetry install --no-interaction

# Full local gate (mirrors CI quality-control)
pre-commit run --all-files
poetry run pytest
/bin/bash ./deploy/test.sh

# Supply chain (poetry check, version metadata, pip-audit)
/bin/bash .github/scripts/supply_chain_check.sh

# Strata layout validation
/bin/bash .github/scripts/strata_check.sh
```

Coverage output: `docs/coverage.xml`. Pre-commit config: [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

**Note:** `poetry.lock` is gitignored — CI resolves deps via `poetry install` at run time.

---

## Migrations

Alembic lives under `modules/model/`. Use the deploy wrapper:

```bash
# Docker Postgres (local)
/bin/bash ./deploy/alembic.sh upgrade --docker-local --docker-rm

# Explicit URL
/bin/bash ./deploy/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"
```

CI runs upgrade → downgrade → upgrade → `alembic check` when model/migration paths change (`.github/workflows/migration-check.yml`).

When editing SQLModel classes, add an Alembic revision under `modules/model/alembic/versions/`.

---

## Code style and tooling

Detailed rules live in [`.cursor/rules/gen-custom/`](.cursor/rules/gen-custom/). Summary:

| Tool            | Setting                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------- |
| Black           | Line length **120**, target py3.12                                                       |
| isort           | Black profile; first-party: `papita_txnsapi`, `papita_txnsmodel`, `papita_txnsregistrar` |
| mypy            | Gradual typing; tests excluded                                                           |
| pylint / flake8 | Max line 120; complexity 18                                                              |
| Docstrings      | Google style with Args/Returns/Raises                                                    |

Patterns: guard clauses and early returns; `logger = logging.getLogger(__name__)`; DB ops wrapped in try/except with rollback; soft delete by default.

Prefer **minimal diffs** — match surrounding code; do not refactor unrelated areas in the same change.

---

## Documentation sources

Use the right tier for the question:

| Need                    | Where                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------- |
| Session state / backlog | `.strata/memory/`, `.strata/issues/` (see MANIFEST load order)                         |
| Codemap                 | [`.strata/docs/ARCHITECTURE.md`](.strata/docs/ARCHITECTURE.md)                         |
| PPT-031 design program  | [`docs/design/README.md`](docs/design/README.md)                                       |
| Auth contract           | [`docs/design/PPT-031-auth-contract.md`](docs/design/PPT-031-auth-contract.md)         |
| API ↔ model mapping     | [`docs/design/PPT-031-api-model-mapping.md`](docs/design/PPT-031-api-model-mapping.md) |
| Target REST contract    | [`modules/api/README.md`](modules/api/README.md)                                       |
| Issue briefs            | [`docs/issues/`](docs/issues/)                                                         |
| Human README            | [`README.md`](README.md)                                                               |
| CI workflows & scripts  | [`.github/CI.md`](.github/CI.md)                                                       |

Promote durable decisions to `.strata/docs/decisions/` (ADR-NNNN) via `/strata:save`; do not duplicate routing rules here.

---

## Continuous integration

Workflow triggers, local commands, pre-commit inventory, PR gate matrix, and troubleshooting: [`.github/CI.md`](.github/CI.md).

**Agent-critical:**

- **Strata strict mode** — `modules/**` or `deploy/**` changes require matching `.strata/` (or `AGENTS.md` / `CLAUDE.md`) updates. Run `/strata:save` before pushing; if `strata-validate` fails locally, restage memory files and recommit.
- **Local-only hooks** — `strata-validate` and `mcp-config-validate` run on `git commit`; CI skips them (`strata-check.yml` enforces Strata on PRs instead).

---

## PR checklist

Before opening or marking ready for review (commands in [`.github/CI.md`](.github/CI.md#pr-checklist)):

1. `pre-commit run --all-files`
2. `poetry run pytest` (or `./deploy/test.sh`)
3. If dependencies changed: `.github/scripts/supply_chain_check.sh`
4. If model/schema changed: migration + `./deploy/alembic.sh` locally
5. If architecture/decisions/backlog shifted: `/strata:capture` during work, `/strata:save` at end
6. No secrets, `.env` files, or credentials in the diff
7. Keep scope focused — avoid drive-by refactors

Do not create git commits unless the user explicitly asks.

---

## API package (current state)

The API is **not** a runnable FastAPI app yet — only settings and JWT helpers exist:

- `modules/api/src/papita_txnsapi/config/settings.py` — env loading from `modules/api/src/.env`
- `modules/api/src/papita_txnsapi/core/security.py` — `AuthSecurityManager` (singleton JWT encode/decode)

Implement routers/schemas against [`modules/api/README.md`](modules/api/README.md) per the PPT-031 mapping doc. Wire auth through `UsersService` per [`PPT-031-auth-contract.md`](docs/design/PPT-031-auth-contract.md).

---

## Strata session habits

| Command           | When                                                       |
| ----------------- | ---------------------------------------------------------- |
| `/strata:load`    | Start of session — orientation from hot tier               |
| `/strata:capture` | Mid-task — findings, bugs, learnings before compaction     |
| `/strata:save`    | End of session — route knowledge, rebuild views, before PR |

Install the [strata plugin](https://github.com/belousov-petr/strata) in Claude Code or use the equivalent skill in Codex/Cursor.
