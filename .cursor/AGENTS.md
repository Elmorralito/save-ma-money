# save-ma-money — agent instructions

Before memory operations or deep project work, read [`.strata/MANIFEST.md`](../.strata/MANIFEST.md) — the project memory contract (structure, routing rules, load order) — and load per its rules.

Project memory is repo-owned under `.strata/` (strata format, `layout_version: 3`). Do not write project memory to tool-owned paths such as `~/.codex/` or `~/.claude/`.

Keep memory rules out of this file — the manifest owns them. Operational content (build/test commands, code style, conventions, repo etiquette) belongs _here_.

---

## Agent adapter files (single source of truth)

| Path                                        | Role                                                       |
| ------------------------------------------- | ---------------------------------------------------------- |
| **`.cursor/AGENTS.md`**                     | **Canonical** operational guide (edit here)                |
| **`.cursor/CLAUDE.md`**                     | Thin Claude Code adapter → `.cursor/AGENTS.md`             |
| [`.agents/AGENTS.md`](../.agents/AGENTS.md) | Symlink → `.cursor/AGENTS.md` (Strata + Codex entry point) |
| [`.agents/CLAUDE.md`](../.agents/CLAUDE.md) | Symlink → `.cursor/CLAUDE.md`                              |

Edit **only** `.cursor/AGENTS.md` and `.cursor/CLAUDE.md`. Do not duplicate adapter content in `.cursor/rules/` or `.strata/`.

Code-style enforcement stays in [`.cursor/rules/gen-custom/`](rules/gen-custom/).

---

## What this repo is

**save-ma-money** (also referred to as _save-ma-finances_ in README copy) is a Poetry monorepo for Papita financial transaction data: type-safe persistence, migrations, and a FastAPI REST surface.

| Goal            | Detail                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Primary outcome | Auditable PostgreSQL-backed financial data with tested model layer and shippable API ([#25](https://github.com/Elmorralito/save-ma-money/issues/25))                                                                                                                                                                                                                                             |
| Active packages | `papita-txnsmodel` (`modules/model`), `papita-txnsapi` (`modules/api`)                                                                                                                                                                                                                                                                                                                           |
| Not in tree yet | `registrar` / `papita-txnsregistrar` (referenced in pytest paths only)                                                                                                                                                                                                                                                                                                                           |
| Database        | **PostgreSQL only** — DuckDB is deprecated ([#31](https://github.com/Elmorralito/save-ma-money/issues/31))                                                                                                                                                                                                                                                                                       |
| Auth direction  | **Supabase project owns user management + Auth** (PPT-039 / [#49](https://github.com/Elmorralito/save-ma-money/issues/49)): register/login via Supabase Auth; API verifies JWKS and maps `sub` → `users.id`. Local HS256 is **tests only** (`AUTH_PROVIDER=local`). Compose must inject `SUPABASE_*`. See `docs/issues/PPT-039-supabase-auth-reissue.md` and learning `supabase-auth-ownership`. |

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
│   └── api/                    # papita-txnsapi — FastAPI MVP (PPT-032 epic)
│       └── src/papita_txnsapi/
│           ├── main.py         # create_app, lifespan, ASGI app
│           ├── config/settings.py
│           ├── core/           # security, exceptions, db_health, rate_limit
│           ├── dependencies/   # auth, pagination, services
│           ├── routers/v1/     # health, auth, accounts, categories, transactions, movements
│           ├── schemas/        # request/response, query_params, converters
│           └── middleware/
├── deploy/                     # alembic.sh, test.sh, utils.sh
├── docker/database/            # local Postgres 15 Compose
├── docs/design/ · docs/issues/ # human design program (PPT-031)
├── .cursor/                    # canonical agent adapters + gen-custom rules
├── .agents/                    # symlinks to .cursor/ adapters (Codex)
├── .strata/                    # agent memory (hot/warm/cold tiers)
└── .github/workflows/          # CI (quality, security, migrations, strata)
```

Domain entities in the model layer include **accounts**, **transactions**, **categories**, **users**, and account extension tables. Legacy v0 names (`assets`, `liabilities`, `indexers`, `types`) are removed from the v3 schema.

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

**API layer rule:** routers validate auth, map schemas, and delegate to model services — no business logic in routers.

---

## Environment and secrets

Never commit real secrets. Templates live under [`environments/`](../environments/README.md).

| Path                                                  | Purpose                                                |
| ----------------------------------------------------- | ------------------------------------------------------ |
| [`environments/README.md`](../environments/README.md) | How `PAPITA_ENV` / `--env` works                       |
| `environments/<name>/.env.example`                    | Committed templates (`local`, `staging`, `production`) |
| `environments/<name>/.env`                            | **Gitignored** secrets — copy from `.env.example`      |

```bash
cp environments/local/.env.example environments/local/.env   # edit JWT + DATABASE_URL + DB_*
export PAPITA_ENV=local   # default for API Settings, Alembic, Compose
docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d
```

Always set `DATABASE_URL` to a PostgreSQL URL. Omitting it can trigger legacy DuckDB fallback paths.

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

Coverage output: `docs/coverage.xml`. Pre-commit config: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml).

**Note:** `poetry.lock` is gitignored — CI resolves deps via `poetry install` at run time.

**Local pre-commit hooks (not CI):** `strata-validate` and `mcp-config-validate` run on `git commit`; GitHub Actions skips them (`strata-check.yml` enforces Strata on PRs instead).

---

## Migrations

Alembic lives under `modules/model/`. Use the deploy wrapper:

```bash
# Docker Postgres (local)
/bin/bash ./deploy/alembic.sh upgrade --env local --docker-rm

# Explicit URL
/bin/bash ./deploy/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"

# B1 Supabase: always use the direct migrations URL (never transaction pooler :6543)
PAPITA_ENV=staging /bin/bash ./deploy/alembic.sh upgrade --url "$DATABASE_URL_MIGRATIONS"
```

CI runs upgrade → downgrade → upgrade → `alembic check` when model/migration paths change (`.github/workflows/migration-check.yml`).

B1 staging checklist + smoke: [`docs/ops/b1-supabase-deploy-checklist.md`](../docs/ops/b1-supabase-deploy-checklist.md) (optional hosted PG). **PPT-039 Auth:** [`docs/issues/PPT-039-supabase-auth-reissue.md`](../docs/issues/PPT-039-supabase-auth-reissue.md) ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)); smoke `make auth-smoke`. Env layout: [`environments/README.md`](../environments/README.md).

When editing SQLModel classes, add an Alembic revision under `modules/model/alembic/versions/`.

---

## Code style and tooling

Detailed rules live in [`.cursor/rules/gen-custom/`](rules/gen-custom/). Summary:

| Tool            | Setting                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------- |
| Black           | Line length **120**, target py3.12                                                       |
| isort           | Black profile; first-party: `papita_txnsapi`, `papita_txnsmodel`, `papita_txnsregistrar` |
| mypy            | Gradual typing; tests excluded                                                           |
| pylint / flake8 | Max line 120; max args 8; complexity 18                                                  |
| Docstrings      | Google style with Args/Returns/Raises                                                    |

Patterns: guard clauses and early returns; `logger = logging.getLogger(__name__)`; DB ops wrapped in try/except with rollback; soft delete by default.

Prefer **minimal diffs** — match surrounding code; do not refactor unrelated areas in the same change.

**API list routes:** when query filters exceed pylint arg limits, bundle parameters in `schemas/query_params.py` via `Depends(get_*_list_query)` and return `TypedDict` service kwargs for mypy-safe `**` unpacking. Use `_require_uuid()` before passing DTO primary keys to services.

---

## Documentation sources

Use the right tier for the question:

| Need                    | Where                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Session state / backlog | `.strata/memory/`, `.strata/issues/` (see MANIFEST load order)                                                                                    |
| Codemap                 | [`.strata/docs/ARCHITECTURE.md`](../.strata/docs/ARCHITECTURE.md)                                                                                 |
| PPT-031 design program  | [`docs/design/README.md`](../docs/design/README.md) · [`docs/design/ARCHITECTURE.md`](../docs/design/ARCHITECTURE.md)                             |
| Auth contract           | [`docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)     |
| API ↔ model mapping     | [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) |
| Target REST contract    | [`modules/api/README.md`](../modules/api/README.md)                                                                                               |
| Issue briefs            | [`docs/issues/`](../docs/issues/)                                                                                                                 |
| Human README            | [`README.md`](../README.md)                                                                                                                       |
| CI workflows & scripts  | [`.github/CI.md`](../.github/CI.md)                                                                                                               |

Promote durable decisions to `.strata/docs/decisions/` (ADR-NNNN) via `/strata:save`; do not duplicate routing rules here.

---

## Continuous integration

Workflow triggers, local commands, pre-commit inventory, PR gate matrix, and troubleshooting: [`.github/CI.md`](../.github/CI.md).

**Agent-critical:**

- **Strata strict mode** — `modules/**` or `deploy/**` changes require matching `.strata/` (or `.agents/AGENTS.md` / `.agents/CLAUDE.md`, which symlink here) updates. Run `/strata:save` before pushing; if `strata-validate` fails locally, restage memory files and recommit.
- **Local-only hooks** — `strata-validate` and `mcp-config-validate` run on `git commit`; CI skips them (`strata-check.yml` enforces Strata on PRs instead).

---

## PR checklist

Before opening or marking ready for review (commands in [`.github/CI.md`](../.github/CI.md#pr-checklist)):

1. `pre-commit run --all-files`
2. `poetry run pytest` (or `./deploy/test.sh`)
3. If dependencies changed: `.github/scripts/supply_chain_check.sh`
4. If model/schema changed: migration + `./deploy/alembic.sh` locally
5. If architecture/decisions/backlog shifted: `/strata:capture` during work, `/strata:save` at end
6. No secrets, `.env` files, or credentials in the diff
7. Keep scope focused — avoid drive-by refactors
8. Omit regenerated artifacts (`docs/coverage.xml`, badge SVGs) unless CI requires them

Do not create git commits unless the user explicitly asks.

---

## API package (current state)

The API is a **runnable FastAPI app** (`papita_txnsapi.main.create_app`, module-level `app`) with CORS, request logging, global exception handlers, and v1 routers at `/api/v1`.

| Router prefix   | Module                       | Delegates to          | Notes                                                                                                                                  |
| --------------- | ---------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `/health`       | `routers/v1/health.py`       | DB probe + latency    | No auth; includes `/database` communication check ([#45](https://github.com/Elmorralito/save-ma-money/issues/45))                      |
| `/auth`         | `routers/v1/auth.py`         | `UsersService`        | Register, login, profile ([#44](https://github.com/Elmorralito/save-ma-money/issues/44))                                               |
| `/accounts`     | `routers/v1/accounts.py`     | `AccountsService`     | CRUD, extensions, balance ([#46](https://github.com/Elmorralito/save-ma-money/issues/46))                                              |
| `/categories`   | `routers/v1/categories.py`   | `CategoriesService`   | CRUD, hierarchy, global seed read ([#46](https://github.com/Elmorralito/save-ma-money/issues/46))                                      |
| `/transactions` | `routers/v1/transactions.py` | `TransactionsService` | INCOME/EXPENSE CRUD + bulk; TRANSFER excluded from default list ([#47](https://github.com/Elmorralito/save-ma-money/issues/47))        |
| `/movements`    | `routers/v1/movements.py`    | `TransactionsService` | TRANSFER alias — scheduled execute/cancel ([#47](https://github.com/Elmorralito/save-ma-money/issues/47))                              |
| `/reports`      | `routers/v1/reports.py`      | `ReportService`       | Tenant-scoped spending/cash-flow/trends/export; budget-performance 501 ([#48](https://github.com/Elmorralito/save-ma-money/issues/48)) |

| `/budgets` | `routers/v1/budgets.py` | — | Deferred 501 (FR-09 / v4.1) |

**Schemas:** `schemas/accounts.py`, `schemas/categories.py`, `schemas/transactions.py`, `schemas/movements.py`, `schemas/reports.py`, `schemas/query_params.py`; enum slugs via `schemas/converters.py`.

**Auth:** Supabase project owns identity (register/login/session). API: `AUTH_PROVIDER=supabase` → JWKS verify + `ensure_from_auth_subject`. Local HS256 is tests only. See learning `supabase-auth-ownership` and [`ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e).

**Deferred stubs:** transaction split (501 on `POST /transactions/{id}/split`), `GET /reports/budget-performance`, export `xlsx`/`pdf`.

Implement new endpoints against [`modules/api/README.md`](../modules/api/README.md) and [`ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33).

---

## Strata session habits

| Command           | When                                                       |
| ----------------- | ---------------------------------------------------------- |
| `/strata:load`    | Start of session — orientation from hot tier               |
| `/strata:capture` | Mid-task — findings, bugs, learnings before compaction     |
| `/strata:save`    | End of session — route knowledge, rebuild views, before PR |

Install the [strata plugin](https://github.com/belousov-petr/strata) in Claude Code or use the equivalent skill in Codex/Cursor.
