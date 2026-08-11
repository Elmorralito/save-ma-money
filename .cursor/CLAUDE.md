# save-ma-money — Claude adapter

Before memory operations or deep project work, read [`.strata/MANIFEST.md`](../.strata/MANIFEST.md) — the project memory contract (structure, routing rules, load order) — and load per its rules.

Project memory is repo-owned under `.strata/` (strata format, `layout_version: 3`). Do not write project memory to tool-owned paths such as `~/.claude/` or `~/.codex/`.

**Operational details** (setup, architecture, CI, PR checklist, code style) live in [`.cursor/AGENTS.md`](AGENTS.md). [`.agents/AGENTS.md`](../.agents/AGENTS.md) symlinks there — edit **only** `.cursor/AGENTS.md`.

---

## Claude Code quick context

| Topic         | Summary                                                                                                                                                                                                                            |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repo          | Python 3.12 Poetry + Node 22/pnpm monorepo — financial transaction data                                                                                                                                                            |
| Packages      | `papita_txnsmodel`; `papita_txnsapi` (MVP routers); `@papita/web` (`modules/web` — presentation only, **no JS domain logic**)                                                                                                      |
| DB            | PostgreSQL / schema `papita_transactions` only                                                                                                                                                                                     |
| API status    | Runnable app: health, auth, accounts, categories, transactions, movements, reports (+ budgets 501) ([#42](https://github.com/Elmorralito/save-ma-money/issues/42))                                                                 |
| Web epic      | PPT-046 / [#112](https://github.com/Elmorralito/save-ma-money/issues/112) — setup [`modules/web/README.md`](../modules/web/README.md); index [`docs/issues` Part VII](../docs/issues/README.md#part-vii--ppt-046-web-spa-epic-112) |
| Active work   | PPT-032 epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) close-out; open post-MVP PPT-043 Redis [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-044/#89 + PPT-045/#93 closed)                 |
| Design docs   | `docs/design/` (PPT-031 program), `docs/issues/` (briefs incl. PPT-046 Part VII)                                                                                                                                                   |
| Agent memory  | `.strata/` — use strata plugin commands below                                                                                                                                                                                      |
| Adapters      | Canonical: `.cursor/AGENTS.md` + `.cursor/CLAUDE.md`; Strata validates `.agents/` symlinks                                                                                                                                         |
| Cursor skills | `/create-issue`, `/plan-issue`, PR body via `.cursor/skills/` — see [AGENTS.md § Repo Cursor skills](AGENTS.md#repo-cursor-skills)                                                                                                 |

---

## Session workflow (strata plugin)

Install: `/plugin marketplace add belousov-petr/strata` then `/plugin install strata@belousov-petr`

| Step            | Command           | Purpose                                                      |
| --------------- | ----------------- | ------------------------------------------------------------ |
| Start           | `/strata:load`    | Load hot tier: MANIFEST → MEMORY → ACTIVE → project_state    |
| During work     | `/strata:capture` | Persist findings, bugs, learnings before context compacts    |
| End / before PR | `/strata:save`    | Route session knowledge, rebuild issue views, update indexes |

Capture hook logs failed shell commands to `.strata/inbox/` automatically when the plugin is enabled.

**CI enforces:** code changes under `modules/**` require matching `.strata/` updates (`strata-check.yml` strict mode). Save before push when you touched architecture or backlog.

**Local pre-commit:** `strata-validate` and `mcp-config-validate` mirror CI checks on commit (skipped in GitHub Actions). See [`.cursor/AGENTS.md` — Local pre-commit hooks](AGENTS.md#setup-test-and-quality).

---

## Where Claude should look first

1. [`.strata/MANIFEST.md`](../.strata/MANIFEST.md) — memory routing (always for memory ops)
2. [`.cursor/AGENTS.md`](AGENTS.md) — build, test, layers, env, API routers, PR checklist, Cursor skills
3. [`.strata/docs/ARCHITECTURE.md`](../.strata/docs/ARCHITECTURE.md) — module codemap
4. Task-specific warm docs per MANIFEST table (`docs/design/`, `docs/issues/`, API endpoint spec)
5. Before implementing a child issue: [`.cursor/skills/plan-issue/`](skills/plan-issue/) (`/plan-issue`) when dependency readiness or an action plan is needed

Do not bulk-load cold archives or all learnings — load on demand per MANIFEST load order.

---

## Claude-specific guardrails

- **Secrets:** never write real credentials; use `.env.example` placeholders only
- **Scope:** minimal diffs; no unrelated refactors or commits unless asked
- **Migrations:** any SQLModel change needs an Alembic revision — see `.cursor/AGENTS.md`
- **Auth:** follow `docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e` when touching login/JWT/users
- **API wiring:** business logic stays in `papita_txnsmodel` services; routers map schemas + `owner` only
- **List filters:** use `Depends(get_*_list_query)` + `TypedDict` service kwargs when adding filtered list routes
- **DB:** PostgreSQL only — do not add DuckDB URLs or dialects
- **API start:** prefer `make api-up` (Compose uvicorn); do not promote host Poetry uvicorn for B0
- **Adapters:** edit `.cursor/AGENTS.md` / `.cursor/CLAUDE.md` only — never duplicate into `.strata/` or rules

For code style enforcement details, see [`.cursor/rules/gen-custom/`](rules/gen-custom/) (also applies when using Claude in Cursor).
