# plan-issue — architect subagent

## Possibility

**YES.** Same pattern as [audit-subagent.md](audit-subagent.md): Cursor `Task` + `subagent_type: generalPurpose`, with role and **stack specialization** encoded in the prompt. There is no built-in “architect” agent type.

**Not suitable:** `bugbot` / `security-review` (fixed prompts); `explore` alone (no structured strategy validation); parent-only critique as the sole architecture gate.

**Does not replace** the SME pre-presentation audit. Architect improves **Strategy**; SME auditor gates the **human-ready action plan**.

## Placement

```text
Strategy v1 (parent)
  → Architect subagent (stack-specialized)
  → Strategy v2 (parent merges deltas + risk addenda)
  → Action plan (parent)
  → SME audit subagent
  → Present to human
```

Skip the Architect subagent only when go/no-go is **NO-GO** and you stop at a readiness report with no strategy (or when planning only the blocker — then run Architect on the **blocker** strategy).

## Stack selection (parent sets role)

Derive from child `[domain]`, labels, issue body, and paths. Set **primary** stack; list secondary as consulting lenses.

| Signal                            | Architect specialization (primary)                                        |
| --------------------------------- | ------------------------------------------------------------------------- |
| `[model]` / Alembic / DTO-service | Postgres · SQLModel · Alembic · service/repository layering               |
| `[api]` / FastAPI routers         | FastAPI · Pydantic v2 · auth/owner scoping · OpenAPI contracts            |
| Web / SPA / `modules/web`         | React · Vite · TanStack Query · BFF cookie session (no TS domain logic)   |
| `[infra]` / Docker / Actions      | Docker · Compose · GH Actions · registry/ops                              |
| Mixed child                       | Primary = dominant deliverable domain; secondary stacks listed explicitly |

If stack cannot be determined → do **not** invoke. Emit `BLOCKED: missing stack` and ask the human/planner what to specialize on.

## Parent: how to invoke

1. Draft **Strategy v1** (approach, touchpoints, layering, tests/B0, non-goals, risk register). Number strategy points as `S1`, `S2`, … for the auditor.
2. Select stack specialization (table above).
3. Read this file; call `Task`:
   - `subagent_type`: `generalPurpose`
   - `model`: `inherit` (unless user named an allowed model)
   - `description`: e.g. `API architect review` / `Model architect review` (≤5 words, stack-specific)
   - `run_in_background`: `false`
   - `prompt`: filled template below
4. Merge report into **Strategy v2** (apply patch list; add suggested risks as new `R#`).
5. On Architect `FAIL` / many `incorrect` points: fix Strategy and re-invoke **once**.
6. Proceed to action plan only after Strategy v2 absorbs the review (or documents accepted disagreements as `open_question` risks).

**Fallback:** if `Task` unavailable, parent runs the same output schema and labels `Architect review: … (parent fallback — subagent unavailable)`.

## Subagent prompt template

Copy into the `Task` `prompt` parameter. Replace `{{…}}`.

```text
You are an Architect specialized in: {{STACK_SPECIALIZATION}}.
Secondary consulting lenses (optional): {{SECONDARY_STACKS_OR_NONE}}.

You are reviewing strategy for the save-ma-money monorepo. You did NOT author this strategy.
Your job: architectural overview + validate EACH numbered strategy point. Do not implement code. Do not write the full action plan.

## Context
- Child issue: {{CHILD_ISSUE_URL_OR_NUMBER}} ({{CHILD_TITLE}})
- Parent epic: {{EPIC_URL_OR_NUMBER}} ({{EPIC_TITLE}})
- Domain / step: {{DOMAIN}} / {{STEP}}
- Go/no-go claimed: {{GO|GO_WITH_HOLDS|NO_GO}}
- Dependency readiness summary: {{DEP_TABLE_OR_BULLETS}}
- Workspace root: {{REPO_ROOT}}

## Strategy under review (v1 or candidate)
{{STRATEGY_MARKDOWN_WITH_S_IDS}}

## Monorepo constraints (enforce for this stack)
- Child = deliverable boundary; epic = context only.
- Model owns domain rules (papita_txnsmodel); API routers = auth + schema map + owner scoping only.
- Web = UI + TanStack Query + BFF cookies; no TS port of model services.
- Schema papita_transactions; soft delete active/deleted_at.
- B0 Docker Postgres default acceptance; Supabase Auth ≠ Supabase PG gate.
- Prefer repo/issue evidence; label assumptions.

## Required work
1. Confirm your specialization matches the issue; if wrong/missing, return BLOCKED: missing stack.
2. Skim repo paths relevant to contested strategy claims (cite evidence). Do not implement.
3. Write a short architectural overview (fit, contracts, tenancy/auth, deps, B0/tests).
4. Validate EVERY strategy point S1..Sn with status: sound | weak | incorrect | missing | out_of_scope.
5. Propose Strategy v2 patch list (deltas only) and risk register addenda (new R# suggestions).
6. Return ONLY the report format below.

## Output format (mandatory)

# Architect strategy review

**Verdict:** SOUND | SOUND WITH GAPS | UNSOUND | BLOCKED: missing stack
**Architect role:** {{STACK_SPECIALIZATION}} (subagent)
**Secondary lenses:** {{SECONDARY_STACKS_OR_NONE}}

## Architectural overview
- Fit to layering: …
- Contract direction (who owns rules): …
- Tenancy / auth: …
- Dependency honesty: …
- Test / B0 implications: …
- Risk register alignment: …

## Per-point validation
| ID | Status | Evidence | Required change |
| -- | ------ | -------- | --------------- |
| S1 | sound\|weak\|incorrect\|missing\|out_of_scope | path or assumption | … |
| S2 | … | … | … |

## Strategy v2 patch list
1. …
2. …

## Risk addenda (suggested)
| ID | Risk | Disposition | Note |
| -- | ---- | ----------- | ---- |
| R… | … | mitigate\|open_question\|accept | … |

## Critical architectural blockers
- … (empty if none)

## Notes for planner
- Short bullets only; do not paste a full rewritten strategy document.
```

## Parent: interpreting results

| Verdict                  | Parent action                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `SOUND`                  | Merge any minor notes; emit Strategy v2; continue to action plan                                                         |
| `SOUND WITH GAPS`        | Apply patch list + risk addenda; Strategy v2 must address gaps                                                           |
| `UNSOUND`                | Apply patches; re-invoke Architect **once**; if still UNSOUND, continue only with explicit `open_question` risks / holds |
| `BLOCKED: missing stack` | Stop; clarify stack with human; do not invent specialization                                                             |

Disagreement with the architect: allowed only if recorded as an `open_question` (human decides) — do not silently drop `incorrect` / blocker findings.
