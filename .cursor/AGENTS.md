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

**save-ma-money** (also referred to as _save-ma-finances_ in README copy) is a Poetry + pnpm monorepo for Papita financial transaction data: type-safe persistence, migrations, a FastAPI REST surface, and a presentation-only React SPA.

| Goal            | Detail                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary outcome | Auditable PostgreSQL-backed financial data with tested model layer, shippable API ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)), and web client ([#112](https://github.com/Elmorralito/save-ma-money/issues/112))                                                                                                                                                                                 |
| Active packages | `papita-transactions-model` → import `papita_txnsmodel` (`modules/model`, PyPI); `papita-transactions-api` → import `papita_txnsapi` (`modules/api`); `@papita/web` (`modules/web`, pnpm — **no JS domain logic**)                                                                                                                                                                                                  |
| Database        | **PostgreSQL only** ([#31](https://github.com/Elmorralito/save-ma-money/issues/31)). Do not add DuckDB URLs or dialect work.                                                                                                                                                                                                                                                                                        |
| Auth direction  | **Supabase project owns user management + Auth** (PPT-039 / [#49](https://github.com/Elmorralito/save-ma-money/issues/49)): register/login via Supabase Auth; API verifies JWKS and maps `sub` → `users.id`. Local HS256 is **tests only** (`AUTH_PROVIDER=local`). Compose must inject `SUPABASE_*`. See `docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49` and learning `supabase-auth-ownership`. |
| Web epic        | PPT-046 / [#112](https://github.com/Elmorralito/save-ma-money/issues/112) — index in [`docs/issues/README.md` Part VII](../docs/issues/README.md#part-vii--ppt-046-web-spa-epic-112); setup SSOT [`modules/web/README.md`](../modules/web/README.md)                                                                                                                                                                |

---

## Repository map

```
save-ma-money/
├── pyproject.toml              # Poetry workspace root (package-mode = false)
├── pnpm-workspace.yaml         # Node workspace → modules/web
├── modules/
│   ├── model/                  # papita_txnsmodel — domain + Alembic
│   │   ├── src/papita_txnsmodel/
│   │   │   ├── model/          # SQLModel tables (schema: papita_transactions)
│   │   │   ├── access/         # DTOs + repositories per domain
│   │   │   ├── services/       # business logic (BaseService)
│   │   │   ├── handlers/       # load/dump pipelines
│   │   │   └── database/       # SQLDatabaseConnector, upsert helpers
│   │   ├── alembic/            # migrations (alembic.ini in module root)
│   │   └── tests/
│   ├── api/                    # papita_txnsapi — FastAPI MVP (PPT-032 epic)
│   │   └── src/papita_txnsapi/
│   │       ├── main.py         # create_app, lifespan, ASGI app
│   │       ├── config/         # settings, environment, logger
│   │       ├── core/           # security, redis, rate_limit, db_health, …
│   │       ├── dependencies/   # auth, pagination, services, redis
│   │       ├── routers/v1/     # health, auth, accounts, categories, txns, movements, reports, budgets
│   │       ├── schemas/        # request/response, query_params, converters
│   │       └── middleware/
│   └── web/                    # @papita/web — Vite + React SPA (PPT-046 / #112)
│       ├── README.md           # Node 22 + pnpm setup SSOT
│       ├── openapi/            # committed OpenAPI artifact (strategy B)
│       └── src/                # presentation only — no domain logic
├── environments/               # PAPITA_ENV profiles (local|staging|production)
├── bin/                        # alembic.sh, test.sh, smokes, utils.sh, web_e2e_seed.*
├── docker/                     # database/, api/, redis/, docker-compose.yml
├── docs/design/ · docs/issues/ # human design program (PPT-031) + web epic Part VII
├── .cursor/                    # adapters, gen-custom rules, skills
├── .agents/                    # symlinks to .cursor/ adapters (Codex)
├── .strata/                    # agent memory (hot/warm/cold tiers)
└── .github/workflows/          # CI (quality, security, migrations, strata, web-ci, publish)
```

Domain entities in the model layer include **accounts**, **transactions**, **categories**, **users**, and account extension tables. Canonical B0 API start: `make api-up` (uvicorn in-container; see ARCHITECTURE Part IX). Full local stack + health wait: `make api-all` (preferred before `make web-dev`).

**Web setup (pnpm ≠ Poetry):** Node **22** + pnpm **9** via root `pnpm-workspace.yaml` / `packageManager`. Install with `pnpm install` (not `poetry install`). Day-to-day: `make web-dev` / `web-lint` / `web-test` / `web-build`. Do **not** port `papita_txnsmodel` rules into TypeScript — UI + TanStack Query + BFF session only. SSOT: [`modules/web/README.md`](../modules/web/README.md). Field RUM / Sentry deferred post-MVP; lab Lighthouse/CWV only in PPT-056 / [#121](https://github.com/Elmorralito/save-ma-money/issues/121).

**Web OpenAPI types (PPT-065):** strategy **B** — committed `modules/web/openapi/openapi.json` + `openapi-typescript` → `modules/web/src/types/api.d.ts`. After API/model OpenAPI-affecting changes run `make web-openapi`. CI: `web-ci.yml` (`check-types`) + `openapi-contract.yml` (artifact vs offline `app.openapi()`; paths include API src + model `model/`/`access/`). Exporter normalizes `info.version`. See `modules/web/README.md`.

**Web thin API client (PPT-048):** `modules/web/src/api/` — `apiFetch` (`credentials: 'include'`, no Bearer), `queryKeys` / `queryOptions`, `PapitaApiError` + discovery headers, health/meta probes only. Domain logic stays in Python.

**Web BFF cookie auth (PPT-049 / PPT-059):** API `/api/v1/bff/auth/*` + `BffSessionStore` (Redis or memory; **not** JWT denylist). Cookie `papita_sid` (HttpOnly); CSRF `X-Papita-CSRF`. SPA login/register + `RequireAuth`; `get_current_owner` accepts Bearer **or** BFF cookie. `make auth-smoke` (Bearer) still valid alongside BFF — it does **not** prove Redis BFF durability. B0 single-worker may use memory when `REDIS_ENABLED=false`; Compose/staging/multi-worker require Redis (`papita:{env}:bff:session:{id}`). When `REDIS_ENABLED`, BFF store is **fail-closed** (503, no memory fallback). Matrix: `modules/web/README.md` + `modules/api/README.md` § Workers/Redis.

**Web accounts/categories UI (PPT-052 / #117):** presentation-only screens under `modules/web/src/pages/{Accounts,AccountDetail,Categories}Page.tsx` + `components/{accounts,categories}/`. Forms use Zod + RHF (`src/forms/`, PPT-055 / #120). Global category write 404 → read-only UX.

**Web quality gate (PPT-056 / #121):** Vitest coverage in `web-ci`; Playwright critical path + axe + Lighthouse in `web-e2e.yml` (Compose). `globalSetup` → `make web-e2e-seed` only (PPT-061 / #126). Auth assumptions: PPT-060 / #125 (confirmed seed user). CSP headers deferred to PPT-057 / #122.

**Local Supabase email confirm:** `AUTH_AUTO_CONFIRM_EMAIL` (default on for `PAPITA_ENV=local`) + service role → Admin register without SMTP; login auto-confirm only when Auth email is unconfirmed (see `modules/api/README.md` Authentication).

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

First-party import roots: `papita_txnsmodel`, `papita_txnsapi`.

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

Always set `DATABASE_URL` to a PostgreSQL URL.

---

## Setup, test, and quality

Python **3.12** recommended. Poetry **2.1.3** (matches CI). Web: Node **22** + pnpm **9** (separate toolchain; see above).

```bash
# Install Python workspace (path deps: model + api)
poetry install --no-interaction

# Install web workspace (modules/web) — does not replace Poetry
pnpm install

# Full local gate (mirrors CI quality-control)
pre-commit run --all-files
poetry run pytest
/bin/bash ./bin/test.sh
make web-lint && make web-test   # Node gate locally; web-ci.yml in Actions

# Supply chain (poetry check, version metadata, pip-audit)
/bin/bash .github/scripts/supply_chain_check.sh

# Strata layout validation
/bin/bash .github/scripts/strata_check.sh
```

Coverage output: `docs/coverage.xml` from `--cov=modules/{model,api}/src` (Codecov-aligned). B0 CI uses `AUTH_PROVIDER=local` against Docker Postgres. **Supabase is Auth-only** (users/tokens) — validate with `make auth-smoke`; do not treat Supabase PG/pooler as an epic or PPT-040 gate. Pre-commit: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml).

**Note:** `poetry.lock` is gitignored — CI resolves deps via `poetry install` at run time. Web `pnpm-lock.yaml` **is** committed.

**Local pre-commit hooks (not CI):** `strata-validate` and `mcp-config-validate` run on `git commit`; staging `modules/web/**` also runs `web-eslint` / `web-prettier` / `web-tsc` / `web-vitest-related` (requires `pnpm install`). GitHub Actions skips those local hooks (`strata-check.yml` / `web-ci.yml` are the CI gates).

---

## Migrations

Alembic lives under `modules/model/`. Use the `bin/` wrapper:

```bash
# Docker Postgres (local)
/bin/bash ./bin/alembic.sh upgrade --env local --docker-rm

# Explicit URL
/bin/bash ./bin/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"

# B1 Supabase: always use the direct migrations URL (never transaction pooler :6543)
PAPITA_ENV=staging /bin/bash ./bin/alembic.sh upgrade --url "$DATABASE_URL_MIGRATIONS"
```

CI runs upgrade → downgrade → upgrade → `alembic check` when model/migration paths change (`.github/workflows/migration-check.yml`).

B1 staging checklist + smoke: [`docs/design/README.md` § Ops](../docs/design/README.md#optional-b1-hosted-postgres-pooler) (optional hosted PG). **PPT-039 Auth:** [`docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49`](../docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49) ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)); smoke `make auth-smoke`. Env layout: [`environments/README.md`](../environments/README.md). PPT-044: [`ARCHITECTURE.md` Part VIII](../docs/design/ARCHITECTURE.md#part-viii--post-mvp-api-hardening-ppt-044-89). PPT-045: [`ARCHITECTURE.md` Part IX](../docs/design/ARCHITECTURE.md#part-ix--uvicorn-process-packaging-ppt-045-93).

When editing SQLModel classes, add an Alembic revision under `modules/model/alembic/versions/`.

---

## Code style and tooling

Detailed rules live in [`.cursor/rules/gen-custom/`](rules/gen-custom/). Summary:

| Tool            | Setting                                                          |
| --------------- | ---------------------------------------------------------------- |
| Black           | Line length **120**, target py3.12                               |
| isort           | Black profile; first-party: `papita_txnsapi`, `papita_txnsmodel` |
| mypy            | Gradual typing; tests excluded                                   |
| pylint / flake8 | Max line 120; max args 8; complexity 18                          |
| Docstrings      | Google style with Args/Returns/Raises                            |

Patterns: guard clauses and early returns; `logger = logging.getLogger(__name__)`; DB ops wrapped in try/except with rollback; soft delete by default.

Prefer **minimal diffs** — match surrounding code; do not refactor unrelated areas in the same change.

**API list routes:** when query filters exceed pylint arg limits, bundle parameters in `schemas/query_params.py` via `Depends(get_*_list_query)` and return `TypedDict` service kwargs for mypy-safe `**` unpacking. Use `_require_uuid()` before passing DTO primary keys to services.

---

## Documentation sources

Use the right tier for the question:

| Need                         | Where                                                                                                                                                                                                |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Session state / backlog      | `.strata/memory/`, `.strata/issues/` (see MANIFEST load order)                                                                                                                                       |
| Codemap                      | [`.strata/docs/ARCHITECTURE.md`](../.strata/docs/ARCHITECTURE.md)                                                                                                                                    |
| PPT-031 design program       | [`docs/design/README.md`](../docs/design/README.md) · [`docs/design/ARCHITECTURE.md`](../docs/design/ARCHITECTURE.md)                                                                                |
| Auth contract                | [`docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)                                                        |
| API ↔ model mapping          | [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33)                                                    |
| Target REST contract         | [`modules/api/README.md`](../modules/api/README.md)                                                                                                                                                  |
| Issue briefs                 | [`docs/issues/README.md`](../docs/issues/README.md) (merged SSOT; Parts I–VII incl. PPT-046 web epic)                                                                                                |
| Web SPA setup / no domain JS | [`modules/web/README.md`](../modules/web/README.md) · epic [#112](https://github.com/Elmorralito/save-ma-money/issues/112)                                                                           |
| Post-MVP hardening / uvicorn | [`ARCHITECTURE.md` Part VIII](../docs/design/ARCHITECTURE.md#part-viii--post-mvp-api-hardening-ppt-044-89) · [Part IX](../docs/design/ARCHITECTURE.md#part-ix--uvicorn-process-packaging-ppt-045-93) |
| Human README                 | [`README.md`](../README.md)                                                                                                                                                                          |
| CI workflows & scripts       | [`.github/CI.md`](../.github/CI.md)                                                                                                                                                                  |

Promote durable decisions to `.strata/docs/decisions/` (ADR-NNNN) via `/strata:save`; do not duplicate routing rules here.

---

## Continuous integration

Workflow triggers, local commands, pre-commit inventory, PR gate matrix, and troubleshooting: [`.github/CI.md`](../.github/CI.md).

**Agent-critical:**

- **Strata strict mode** — `modules/**` or `bin/**` changes require matching `.strata/` (or `.agents/AGENTS.md` / `.agents/CLAUDE.md`, which symlink here) updates. Run `/strata:save` before pushing; if `strata-validate` fails locally, restage memory files and recommit.
- **Local-only hooks** — `strata-validate` and `mcp-config-validate` run on `git commit`; CI skips them (`strata-check.yml` enforces Strata on PRs instead).

---

## PR checklist

Before opening or marking ready for review (commands in [`.github/CI.md`](../.github/CI.md#pr-checklist)):

1. `pre-commit run --all-files`
2. `poetry run pytest` (or `./bin/test.sh`)
3. If dependencies changed: `.github/scripts/supply_chain_check.sh`
4. If model/schema changed: migration + `./bin/alembic.sh` locally
5. If architecture/decisions/backlog shifted: `/strata:capture` during work, `/strata:save` at end
6. No secrets, `.env` files, or credentials in the diff
7. Keep scope focused — avoid drive-by refactors
8. Omit regenerated artifacts (`docs/coverage.xml`, badge SVGs) unless CI requires them
9. Fill [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) for the PR body (skill: `.cursor/skills/pr-description/`)
10. New GitHub issues: use [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) (epic / program / child / bug) per [github_issue_conventions](rules/gen-custom/github_issue_conventions.mdc); agent skill: [`.cursor/skills/create-issue/`](skills/create-issue/) (`/create-issue`)
11. Optional CI opt-outs on PRs: durable `skip-*` labels only ([`.github/CI.md` § PR skip labels](../.github/CI.md#pr-skip-labels)) — never invent `PPT-*` labels

Do not create git commits unless the user explicitly asks.

---

## API package (current state)

The API is a **runnable FastAPI app** (`papita_txnsapi.main.create_app`, module-level `app`) with CORS, request logging, global exception handlers, and v1 routers at `/api/v1`.

| Router prefix   | Module                       | Delegates to          | Notes                                                                                                                                                                                     |
| --------------- | ---------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/health`       | `routers/v1/health.py`       | DB probe + latency    | No auth; includes `/database` communication check ([#45](https://github.com/Elmorralito/save-ma-money/issues/45))                                                                         |
| `/auth`         | `routers/v1/auth.py`         | `UsersService`        | Register, login, `/me`, OAuth/SSO; Supabase refresh/logout ([#44](https://github.com/Elmorralito/save-ma-money/issues/44), [#49](https://github.com/Elmorralito/save-ma-money/issues/49)) |
| `/accounts`     | `routers/v1/accounts.py`     | `AccountsService`     | CRUD, extensions, balance ([#46](https://github.com/Elmorralito/save-ma-money/issues/46))                                                                                                 |
| `/categories`   | `routers/v1/categories.py`   | `CategoriesService`   | CRUD, hierarchy, global seed read ([#46](https://github.com/Elmorralito/save-ma-money/issues/46))                                                                                         |
| `/transactions` | `routers/v1/transactions.py` | `TransactionsService` | INCOME/EXPENSE CRUD + bulk; TRANSFER excluded from default list ([#47](https://github.com/Elmorralito/save-ma-money/issues/47))                                                           |
| `/movements`    | `routers/v1/movements.py`    | `TransactionsService` | TRANSFER alias — scheduled execute/cancel ([#47](https://github.com/Elmorralito/save-ma-money/issues/47))                                                                                 |
| `/reports`      | `routers/v1/reports.py`      | `ReportService`       | Tenant-scoped spending/cash-flow/trends/export; budget-performance 501 ([#48](https://github.com/Elmorralito/save-ma-money/issues/48))                                                    |

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
