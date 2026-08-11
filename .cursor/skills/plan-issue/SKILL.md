---
name: plan-issue
description: >
  Reviews a GitHub child issue against its parent epic, checks Depends on /
  Blocks readiness, drafts strategy, runs a stack-specialized Architect
  subagent, generates a roadmap action plan via a PM/BA subagent, then runs
  a SME technical-expert subagent audit before presenting (plan only — no
  code). Use when the user asks to plan an issue, strategy for a PPT child,
  /plan-issue, or whether an issue is blocked by dependencies.
disable-model-invocation: true
---

# Plan issue (project)

Turn a **child issue + parent epic** into a dependency-aware implementation plan.
**Plan only** — do not implement code unless the user explicitly asks after the plan.

This skill lives at `.cursor/skills/plan-issue/` (repo-only).

**Independent of `/create-issue`.** Do not invoke, chain, or require issue creation
as part of this skill. Plan only against an existing child + epic the user names.

**Indexed from:** [`.cursor/AGENTS.md`](../../AGENTS.md) · [`.cursor/README.md`](../../README.md) ·
[`.agents/skills/plan-issue`](../../../.agents/skills/plan-issue) (symlink) ·
[`project_adapters.mdc`](../../rules/gen-custom/project_adapters.mdc) ·
[`github_issue_conventions.mdc`](../../rules/gen-custom/github_issue_conventions.mdc) ·
[`docs/issues/README.md`](../../../docs/issues/README.md).

## Inputs

Require (ask if missing):

| Input       | Examples                                          |
| ----------- | ------------------------------------------------- |
| Child issue | `#166`, URL, or `PPT-073`                         |
| Parent epic | `#163`, URL, or from child's **Parent epic** line |

Optional: sibling issues listed under Depends on / Blocks.

Resolve via `gh issue view <N> --repo Elmorralito/save-ma-money` (or origin remote).

## Progress checklist

```
Plan-issue progress:
- [ ] 1. Intake — fetch child + epic; extract goal, AC, depends/blocks, OOS
- [ ] 2. Dependency readiness — verify each Depends on (issue state + repo evidence)
- [ ] 3. Go / no-go — can address now, or must finish a dependency first
- [ ] 4. Repo current state — cite paths for this child's domain
- [ ] 5. Strategy v1 — numbered points S# + risk register
- [ ] 6. Architect subagent (stack-specialized) → merge into Strategy v2
- [ ] 7. PM/BA subagent — roadmap action plan from Strategy v2 (or NO-GO stub)
- [ ] 8. Parent light merge → SME/tech-expert **subagent** audit
- [ ] 9. Apply audit fixes (re-audit once if FAIL); then present to human
```

## Repo constraints (always apply)

### Scope & hierarchy

- **Child = deliverable boundary.** Plan only what the child issue’s tasks, AC, and out-of-scope allow.
- **Epic = context, not a work order.** Use it for intent, layering rules, dependency graph, deferred items, and epic-level OOS — not to pull sibling PPT work into this plan.
- **Do not expand** into sibling PPT issues unless go/no-go is **NO-GO** and you redirect planning to the blocking dependency (or the user asks to plan that sibling).
- **Depends on / Blocks** from the child body are authoritative for sequencing; reconcile with the epic’s mermaid/order table when they disagree (call it out as a risk / open question).
- Titles and PPT ids follow `.cursor/rules/gen-custom/github_issue_conventions.mdc` (`{semantic}/PPT-{NNN}: [{domain}] …`; children reuse parent `EPIC: PPT-*` label).

### Domain → primary paths

Match the child’s `[domain]` (and issue labels) to where the plan may touch code:

| Domain          | Package / import   | Primary paths                                                          | Plan must respect                                                                                |
| --------------- | ------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `[model]`       | `papita_txnsmodel` | `modules/model/src/`, `modules/model/tests/`, `modules/model/alembic/` | SQLModel + services/repos; schema `papita_transactions`; soft delete via `active` / `deleted_at` |
| `[api]`         | `papita_txnsapi`   | `modules/api/src/`, `modules/api/tests/`                               | Routers under `routers/v1/`; schemas; deps — **no** domain rules in routers                      |
| Web / SPA       | `@papita/web`      | `modules/web/` (`src/`, `openapi/`, `e2e/`)                            | UI + TanStack Query + BFF cookies only — **no** TS port of model services                        |
| `[infra]` / ops | —                  | `bin/`, `docker/`, `.github/`, `Makefile`                              | Only if the child is ops/ci-scoped                                                               |

Cross-cutting OpenAPI sync / docs gates often live on a later sibling (e.g. PPT-075) — do not absorb them unless this child’s AC explicitly requires them.

### Layering rules (non-negotiable in plans)

- **API layer rule:** routers validate auth, map request/response schemas, enforce `owner` / tenant scoping, and **delegate** to `papita_txnsmodel` `*Service` methods. Reject plan tasks that “add business logic in the router.”
- **Model owns domain:** create/update/query/mark-paid/upcoming-window rules stay in model services/repos; API and web consume them.
- **Web domain boundary:** presentation, forms, Query keys, BFF session (`papita_sid` / CSRF) — never reimplement `UsersService` or other model methods in JS (see `modules/web/README.md` § Domain boundary).
- **Auth posture:** Supabase owns identity for real runs; `AUTH_PROVIDER=local` is B0/pytest only. Plans that touch auth should say Bearer vs BFF cookie and align with existing `get_current_owner` patterns — do not invent a new auth stack.
- **Secrets:** never put credentials, tokens, or private URLs in the plan; name env vars only (e.g. `DATABASE_URL`, `SUPABASE_*`).

### Platform (B0 / B1)

- **B0 (default acceptance):** Docker Postgres (+ Compose API/Redis when the step needs them). Canonical API: `make api-up` / stack: `make api-all`. Domain children validate here unless the issue says otherwise.
- **Auth smoke:** `make auth-smoke` when the step touches auth; not required for pure CRUD wiring that reuses existing deps.
- **B1 pooler (`:6543`):** optional hosted Postgres connectivity — **not** an Auth or epic gate. Alembic/migrations use direct `:5432` (`DATABASE_URL_MIGRATIONS`) when migrations are in scope.
- **Supabase PG/pooler** is not a substitute for B0 acceptance of model/API work.

### Evidence over invention

- Prefer **issue bodies + inspected repo paths** over memory. Cite files/symbols when claiming a dependency is `ready`.
- Label **assumptions** explicitly; if a contract is unverified, use dependency status `unknown` / `partial` and an open question — do not invent green readiness.
- When patterns already exist (list query `Depends`, `_require_uuid`, owner filters, OpenAPI commit path), **plan to match them** instead of proposing a parallel style.

## Step 1 — Intake

From the child and epic, extract:

- Goal / summary, tasks, acceptance criteria
- **Depends on** and **Blocks** (issue numbers + PPT ids)
- Out of scope
- Domain (`api` / `model` / web / infra) and step number in the epic graph

## Step 2 — Dependency readiness (required)

For **each** hard dependency in **Depends on** (and soft deps that gate this step):

1. `gh issue view` — state (`OPEN` / `CLOSED`), title, AC summary.
2. Inspect the repo for the dependency's claimed deliverables (services, migrations, routers, schemas). Cite paths.
3. Classify each dependency:

| Status    | Meaning                                                       |
| --------- | ------------------------------------------------------------- |
| `ready`   | Closed **or** open but contracts exist in-repo and are usable |
| `partial` | Some contracts exist; gaps block parts of the child           |
| `blocked` | Missing or unfinished; child cannot honestly start            |
| `unknown` | Cannot verify — state what evidence is missing                |

Also note what this child **Blocks** (downstream) so the plan leaves a clean handoff surface.

### Go / no-go (emit before strategy)

Pick exactly one:

1. **GO** — dependencies are `ready` (or `partial` with a documented workaround that stays in-scope). Proceed to plan the child.
2. **NO-GO** — at least one hard dependency is `blocked` / insufficient. **Do not** produce a full implementation plan for the child as if it were startable. Instead:
   - Name the blocking issue(s)
   - Summarize what must land first
   - Offer a **minimal plan for the top blocker** (or stop after readiness report if the user only asked about the child)
3. **GO WITH HOLDS** — can start scaffolding/tests/docs that do not call missing APIs; list holds explicitly.

Never invent green dependency status.

## Step 3 — Analysis

Short analysis:

- What “done” means for this child vs epic close-out
- Prerequisite contracts (methods, DTOs, error modes) from deps
- Gaps between issue text and repo reality
- Seed list of candidate risks (refine into the register in Step 4)

## Step 4 — Strategy v1 → Architect subagent → Strategy v2

### 4a — Strategy v1 (parent)

Must cover: approach, endpoint/surface or schema/service touchpoints, mapping to existing layers, auth/owner (if API), tests on B0, explicit non-goals, and a **risk register**.

Number every strategy point as `S1`, `S2`, … so the Architect can validate point-by-point.

### Risk register (create in Strategy; carry forward)

Identify risks while drafting Strategy (not only at the end). For **each** risk, set disposition to exactly one of:

| Disposition     | When to use                                  | Required fields                                            |
| --------------- | -------------------------------------------- | ---------------------------------------------------------- |
| `mitigate`      | Controllable in this child's plan            | Mitigation action + which work-breakdown task owns it      |
| `open_question` | Needs a human decision before or during impl | Question, options/default if any, when it must be answered |
| `accept`        | Known residual; out of scope or deferred     | Why acceptable + deferral target (PPT/issue) if any        |

Use stable ids (`R1`, `R2`, …). Cover at least: dependency/contract fragility, scope bleed, tenancy/auth, test/B0 gaps, and any domain-specific unknowns. Table shape: [reference.md](reference.md) § Risk register.

### 4b — Architect subagent (required when a strategy exists)

Independent **stack-specialized Architect** reviews Strategy v1. Does **not** replace the later SME audit.

1. Select specialization from child domain/stack ([architect-subagent.md](architect-subagent.md) § Stack selection). If unclear → `BLOCKED: missing stack`; ask human.
2. Invoke `Task` (`generalPurpose`, `run_in_background: false`) with the prompt template in [architect-subagent.md](architect-subagent.md).
3. Expect: architectural overview + per-`S#` status (`sound` / `weak` / `incorrect` / `missing` / `out_of_scope`) + Strategy v2 patch list + risk addenda.
4. Merge into **Strategy v2**. On `UNSOUND`, fix and re-invoke Architect **once**. Record unresolved disagreements as `open_question` risks — do not silently drop `incorrect` findings.

**Fallback:** same report schema with label `Architect review: … (parent fallback — subagent unavailable)`.

### 4c — Parent merge checklist (after Architect)

Before freezing Strategy v2, confirm:

1. Scope creep into siblings / epic addressed
2. Missing AC, edge cases, error paths covered or risked
3. Dependency / sequencing gaps honest vs go/no-go
4. Owner scoping / cross-tenant risk (API/data)
5. Test / B0 implications present
6. Architect patch list applied or explicitly deferred as open questions
7. Risk register complete (including Architect addenda)
8. Mitigations actionable / open questions have decision points

Emit **Strategy v2** + what changed (include Architect verdict + role/stack).

## Step 5 — Action plan via PM/BA subagent (only if GO or GO WITH HOLDS)

Independent **Product Manager / BA engineer** subagent turns Strategy v2 into a **roadmap-shaped** action plan. Parent does not author the WBS when `Task` is available.

### 5a — Preconditions

- Strategy v2 frozen after Architect (SOUND or SOUND WITH GAPS with patches applied).
- Do **not** invoke if strategy is UNSOUND / `BLOCKED: missing stack`, or go/no-go is **NO-GO** without a strategy.

### 5b — Invoke PM/BA subagent

1. Read [pm-ba-subagent.md](pm-ba-subagent.md).
2. Call `Task` (`generalPurpose`, `run_in_background: false`, description e.g. `PM BA action plan`).
3. Pass: child/epic context, AC, OOS, go/no-go, dependency table, Architect summary, Strategy v2, current-state paths.
4. Expect: roadmap phases/milestones + `T#` WBS + AC/`S#` traceability + risk/human decisions + DoD + downstream handoff.
5. Verdict: `READY_FOR_SME_AUDIT` | `READY_WITH_HOLDS` | `BLOCKED`.

**Fallback:** parent writes the plan with the same schema and labels `Action plan: … (parent fallback — PM/BA subagent unavailable)`.

### 5c — Parent light merge

Before SME audit, verify:

- Scope lock (in-child only)
- Every child AC maps to a task + DoD evidence
- Risks carried (`mitigate`→`T#`, `open_question`→Human decisions, `accept`→residual)
- No re-architecture that contradicts Strategy v2 / Architect (reject or convert to `open_question`)
- Concrete paths/names retained from strategy

### 5d — NO-GO stub (parent; no PM/BA child plan)

If **NO-GO**, skip PM/BA for the child and emit:

1. Dependency readiness table
2. Blocker summary + risks that reinforce the block
3. Recommended next issue to plan/implement
4. Optional: run Architect → PM/BA on the **blocker** only

## Step 6 — Pre-presentation audit via SME subagent (required before human)

**Do not present** the plan to the human until the independent audit finishes.

### Why a subagent

The planner must not be the sole auditor. Launch a **separate** agent whose role is **Expert subject-matter expert and technical expert** so checklist A–N and risk carry-through get an independent review. This is supported via Cursor `Task` (`generalPurpose`) — see [audit-subagent.md](audit-subagent.md).

### Parent must

1. Keep the draft private (Strategy v2 + PM/BA action plan after light merge, or NO-GO stub).
2. Read [audit-subagent.md](audit-subagent.md) and invoke `Task`:
   - `subagent_type`: `generalPurpose`
   - `description`: short title e.g. `SME plan audit`
   - `run_in_background`: `false`
   - `prompt`: filled template from `audit-subagent.md` (full draft including PM/BA roadmap + child/epic ids + claimed go/no-go + repo root)
3. Wait for the subagent report (`PASS` | `PASS WITH HOLDS` | `FAIL` + A–N table).
4. Apply fixes to the draft. On `FAIL`, re-invoke the subagent **once** with the revised draft.
5. Present only after that loop. Never claim `Audit: PASS` if the last subagent verdict was `FAIL`.

**Fallback:** if `Task` is unavailable, parent runs the same checklist/report format and labels `Audit: … (parent fallback — subagent unavailable)`.

Checklist definitions: [reference.md](reference.md) § Pre-presentation audit. Prompt + interpretation table: [audit-subagent.md](audit-subagent.md).

Include in the presented output (never omit):

- `Audit: PASS` | `PASS WITH HOLDS` | parent-fallback variant
- `Auditor: SME/technical-expert subagent` (or fallback note)
- Holds / critical blockers from the auditor (if any)

## Output rules

- Lead with the **go/no-go** verdict and dependency table.
- Include **Architect** (verdict + stack), **PM/BA** (verdict + roadmap author), and **SME audit** results.
- Surface the **risk register** and any **open questions** for human readiness before the work breakdown.
- Present **only after** Step 6 (or Step 6 with declared holds).
- Keep epic context visible; do not expand scope into other PPT steps.
- Do not write production code, open PRs, or close issues as part of this skill.
- Never put secrets, tokens, or credentialed URLs in the plan.
