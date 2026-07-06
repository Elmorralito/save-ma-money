# save-ma-money — Claude adapter

Before memory operations or deep project work, read [`.strata/MANIFEST.md`](.strata/MANIFEST.md) — the project memory contract (structure, routing rules, load order) — and load per its rules.

Project memory is repo-owned under `.strata/` (strata format, `layout_version: 3`). Do not write project memory to tool-owned paths such as `~/.claude/` or `~/.codex/`.

**Operational details** (setup, architecture, CI, PR checklist, code style) live in [`AGENTS.md`](AGENTS.md). Read that file for anything not covered here.

---

## Claude Code quick context

| Topic        | Summary                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------ |
| Repo         | Python 3.12 Poetry monorepo — financial transaction data                                               |
| Packages     | `papita-txnsmodel` (implemented), `papita-txnsapi` (scaffold)                                          |
| DB           | PostgreSQL / schema `papita_transactions` — no new DuckDB work                                         |
| API status   | Settings + JWT only; routers not built ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)) |
| Design docs  | `docs/design/` (PPT-031 program), `docs/issues/` (briefs)                                              |
| Agent memory | `.strata/` — use strata plugin commands below                                                          |

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

**Local pre-commit:** `strata-validate` and `mcp-config-validate` mirror CI checks on commit (skipped in GitHub Actions). See [`AGENTS.md` — Local pre-commit hooks](AGENTS.md#local-pre-commit-hooks-not-ci).

---

## Where Claude should look first

1. [`.strata/MANIFEST.md`](.strata/MANIFEST.md) — memory routing (always for memory ops)
2. [`AGENTS.md`](AGENTS.md) — build, test, layers, env, PR checklist
3. [`.strata/docs/ARCHITECTURE.md`](.strata/docs/ARCHITECTURE.md) — module codemap
4. Task-specific warm docs per MANIFEST table (`docs/design/`, `docs/issues/`, API endpoint spec)

Do not bulk-load cold archives or all learnings — load on demand per MANIFEST load order.

---

## Claude-specific guardrails

- **Secrets:** never write real credentials; use `.env.example` placeholders only
- **Scope:** minimal diffs; no unrelated refactors or commits unless asked
- **Migrations:** any SQLModel change needs an Alembic revision — see `AGENTS.md`
- **Auth:** follow `docs/design/PPT-031-auth-contract.md` when touching login/JWT/users
- **Deprecated:** do not add DuckDB URLs or reintroduce registrar assumptions without checking the tree

For code style enforcement details, see [`.cursor/rules/gen-custom/`](.cursor/rules/gen-custom/) (also applies when using Claude in Cursor).
