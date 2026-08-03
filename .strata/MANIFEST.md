---
layout_version: 3
---

# MANIFEST — save-ma-money

**Open this first.** The project-owned memory contract for every AI tool working in this repo — and the _only_ place structure and routing live. Other files (including `memory/MEMORY.md`) index and point; they do not restate this contract.

Initialized 2026-07-06 with [strata](https://github.com/belousov-petr/strata) (memory `layout_version: 3`). Pattern reference: [DESIGN](https://github.com/belousov-petr/strata/blob/main/docs/DESIGN.md) · upgrades: [MIGRATIONS](https://github.com/belousov-petr/strata/blob/main/MIGRATIONS.md).

## Invocation — works the same for every tool

This memory is maintained by the **strata** skill; the operations named below (**save**, **load**, **capture**, **init**) are invoked per tool:

- **Claude Code (plugin):** `/strata:init` · `/strata:save` · `/strata:load` · `/strata:capture`.
- **Codex and other tools:** `Skill(name='strata', args='init')`, `Skill(name='strata', args='capture')`, and the skill's default rule lookup driving the same save/load flow.

The `/strata:save`-style references throughout this file name those operations — a non-Claude agent performs the identical flow through the skill, not by typing a slash command.

## What save-ma-money is

Production-grade Python monorepo for personal/professional financial transaction data: type-safe SQLModel persistence (`papita-txnsmodel`), Alembic migrations, and a FastAPI API layer (`papita-txnsapi`) documented in [`modules/api/README.md`](../modules/api/README.md). "Done" means auditable PostgreSQL-backed data, tested model paths, and a shippable REST API ([#42](https://github.com/Elmorralito/save-ma-money/issues/42) epic).

## Structural overview

```
save-ma-money/
├── .agents/ · .cursor/            tool adapters → this file (thin)
├── README.md                      human front door
├── modules/model/                 papita-txnsmodel (SQLModel, Alembic, services)
├── modules/api/                   papita-txnsapi (FastAPI settings, security)
├── modules/web/                   @papita/web (Vite React SPA; PPT-047…053 ledger screens)
├── docs/design/ · docs/issues/    human design program (pre-Strata)
├── environments/                  PAPITA_ENV profiles (local|staging|production)
├── bin/ · docker/database/        migrations, local Postgres, ops entrypoints
└── .strata/
    ├── MANIFEST.md                this contract (layout_version, routing, load order)
    ├── memory/                    HOT — loads at session start
    │   ├── MEMORY.md              pure index: live pointers + rules-by-trigger table (≤80 lines)
    │   ├── project_state.md       current + last completed session (≤200 lines)
    │   ├── learnings/             operation-keyed behavioral rules (+ generated INDEX.md)
    │   └── archive/               COLD — ARCHIVE.md · action_log.md · old sessions · source-*
    ├── inbox/                     transient capture scratch (git-ignored; promoted by capture/save)
    ├── issues/                    single backlog: findings + tasks + initiatives
    │   ├── ACTIVE.md / OPEN.md / PARKED.md    generated views (edit items, not views)
    │   ├── <id>-<slug>.md         one item per file
    │   └── archive/               resolved / wont-fix
    └── docs/                      WARM — on-demand depth (grow as needed)
        ├── ARCHITECTURE.md        codemap + index into architecture/
        ├── product/ · architecture/ · decisions/ · reference/ · ops/
        └── CHANGELOG.md · roadmap.md   (when they exist)
```

_(Extend with project-specific directories as they develop.)_

## Where do I look for X?

| If you need…                             | Open…                                                                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| What was I doing last session            | `memory/project_state.md`                                                                                           |
| Work in flight right now                 | `issues/ACTIVE.md`                                                                                                  |
| What's on the backlog (by area)          | `issues/OPEN.md`                                                                                                    |
| Deferred work + revive triggers          | `issues/PARKED.md`                                                                                                  |
| A rule before doing operation X          | `memory/MEMORY.md` rules-by-trigger table → `memory/learnings/<slug>.md`                                            |
| Why a decision was made                  | `docs/decisions/ADR-NNNN-*.md`                                                                                      |
| How a subsystem works                    | `docs/ARCHITECTURE.md` → `docs/architecture/<slug>.md`                                                              |
| Product requirements                     | `docs/product/<slug>.md`                                                                                            |
| A stable fact (paths, schemas, APIs)     | `docs/reference/<slug>.md`                                                                                          |
| A procedure / runbook / incident pattern | `.strata/docs/ops/` → human [`docs/design/README.md` § Ops](../docs/design/README.md#ops-redis--optional-b1-pooler) |

| Did we send / post / complete X externally | `memory/archive/action_log.md` (grep) |
| Old sessions, closed issues, provenance | `memory/archive/` · `issues/archive/` (grep) |

## The three tiers

| Tier     | Where                                 | When loaded                     |
| -------- | ------------------------------------- | ------------------------------- |
| **Hot**  | `memory/` + `issues/ACTIVE.md`        | Session start                   |
| **Warm** | `docs/` + individual `issues/*.md`    | On demand, by task              |
| **Cold** | `memory/archive/` + `issues/archive/` | Only on explicit history search |

## Routing — where new knowledge goes

| You produced / discovered                                  | Write to                                                                                          | When                                                             |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Finding, bug, improvement, debt, task, feature, initiative | `issues/<id>-<slug>.md` (copy `issues/_TEMPLATE.md`), status `open`, full rationale + diagnostics | **Immediately, mid-session; use `/strata:capture`**              |
| Deferred work                                              | same file, status `parked` + `revive-when:`                                                       | at capture or triage                                             |
| Behavioral lesson (worked or burned you)                   | `memory/learnings/<slug>.md` (copy `_TEMPLATE.md`)                                                | at `/strata:capture`, `/strata:save`, or immediately if hard-won |
| Shipped decision with rationale                            | `docs/decisions/ADR-NNNN-<slug>.md` (+ source → `memory/archive/source-adr-*`)                    | at `/strata:save`                                                |
| Product requirement                                        | `docs/product/<slug>.md`                                                                          | when it exists                                                   |
| How a subsystem works                                      | `docs/architecture/<slug>.md` (+ row in `ARCHITECTURE.md`)                                        | when it stabilizes                                               |
| Stable fact                                                | `docs/reference/<slug>.md`                                                                        | on second lookup                                                 |
| Procedure, runbook, incident                               | `.strata/docs/ops/…` or `docs/design/README.md` § Ops                                             | when it changes                                                  |
| Session narrative                                          | `memory/project_state.md` (rollover → archive)                                                    | at `/strata:save`                                                |
| Completed external action (PR, email, durable URL)         | `memory/archive/action_log.md` append                                                             | at `/strata:save`                                                |

**Never store:** secret values (env var _names_ only); anything derivable from code or `git log`; raw transcripts, stack traces, command dumps — root cause + evidence instead.

## Capture interrupt (`/strata:capture`)

Use this while working when a command fails, an agent retries with a workaround, a brittle environment rule appears, or a finding is too useful to leave in conversation memory. Route closeable work to `issues/`, reusable behavior to `memory/learnings/`, or both. Do not edit generated views during capture; `/strata:save` regenerates them.

## Load order (`/strata:load`)

1. This file
2. `memory/MEMORY.md`
3. `issues/ACTIVE.md`
4. `memory/project_state.md` (current + last completed only)

Then on demand: `issues/OPEN.md` by area · matching `learnings/<slug>.md` at operation time · specific `docs/**` by task · `archive/` only via explicit grep. **Never bulk-load:** learnings, ADRs, individual issues, anything under `archive/`.

## States and types

- **Issue types:** `bug | improvement | debt | task | feature | initiative`
- **Issue statuses:** `open | in-progress | parked | resolved | wont-fix`
- **Severity:** `high | med | low`
- **Learning origin:** `success | failure`

`parked` requires a concrete `revive-when:` trigger. `resolved`/`wont-fix` are terminal → `issues/archive/` at next `/strata:save`. Status changes are frontmatter edits, not file moves.
