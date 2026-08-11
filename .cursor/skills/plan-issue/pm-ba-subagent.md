# plan-issue — PM / BA action-plan subagent

## Possibility

**YES.** Same pattern as [architect-subagent.md](architect-subagent.md) and [audit-subagent.md](audit-subagent.md): Cursor `Task` + `subagent_type: generalPurpose`, with **Product Manager + BA engineer** role encoded in the prompt. There is no built-in “PM” agent type.

**Not suitable:** `bugbot` / `security-review`; asking the Architect to write the full WBS; asking the SME auditor to author the plan it will audit; parent-only WBS as the sole delivery plan when `Task` is available.

**Does not replace** Architect (strategy) or SME audit (final gate). PM/BA turns Strategy v2 into a **roadmap-shaped action plan**.

## Placement

```text
Strategy v2 (post-Architect merge)
  → PM/BA subagent generates action plan (roadmap)
  → Parent light merge (scope / AC / layering check)
  → SME audit subagent
  → Present to human
```

Skip only when go/no-go is **NO-GO** with no child strategy (parent emits NO-GO stub). If planning the **blocker** instead, run PM/BA on that blocker’s Strategy v2.

**Do not invoke** if Strategy is still `UNSOUND` or Architect returned `BLOCKED: missing stack` without resolution.

## Role

**Product Manager and Business Analyst (BA) engineer** for this PPT child slice.

| Does                                                                        | Does not                                                               |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Phased roadmap + ordered `T#` WBS                                           | Re-architect or override Architect `incorrect` without `open_question` |
| Map every child AC → tasks + DoD evidence                                   | Expand into sibling PPT work                                           |
| Carry risks: mitigate→tasks, open_question→Human decisions, accept→residual | Claim SME `Audit: PASS`                                                |
| Preserve Strategy v2 technical alignments (paths, contracts, non-goals)     | Invent green dependency readiness                                      |
| Define milestones and what unblocks **Blocks** downstream                   | Implement code                                                         |

## Parent: how to invoke

1. Freeze **Strategy v2** (Architect SOUND or SOUND WITH GAPS with patches applied).
2. Gather: child/epic ids, AC, OOS, go/no-go, dependency table, Architect verdict summary, current-state path bullets.
3. Read this file; call `Task`:
   - `subagent_type`: `generalPurpose`
   - `model`: `inherit` (unless user named an allowed model)
   - `description`: e.g. `PM BA action plan` (≤5 words)
   - `run_in_background`: `false`
   - `prompt`: filled template below (include Strategy v2 + template sections from [reference.md](reference.md))
4. **Light merge:** check scope lock, AC coverage, layering (no business logic in API/web), risk carry-through. Fix only clear defects or send back once.
5. Hand merged draft to SME audit ([audit-subagent.md](audit-subagent.md)).

**Fallback:** if `Task` unavailable, parent writes the plan using the same output schema and labels `Action plan: … (parent fallback — PM/BA subagent unavailable)`.

## Subagent prompt template

Copy into the `Task` `prompt` parameter. Replace `{{…}}`.

```text
You are a Product Manager and Business Analyst (BA) engineer for the save-ma-money monorepo.

Role: turn an Architect-approved Strategy v2 into a roadmap-oriented action plan for ONE child issue. You did NOT invent the architecture. Preserve technical alignments from the strategy. Do not implement code. Do not perform the SME audit.

## Context
- Child issue: {{CHILD_ISSUE_URL_OR_NUMBER}} ({{CHILD_TITLE}})
- Parent epic: {{EPIC_URL_OR_NUMBER}} ({{EPIC_TITLE}})
- Domain / step: {{DOMAIN}} / {{STEP}}
- Go/no-go: {{GO|GO_WITH_HOLDS|NO_GO}}
- Holds (if any): {{HOLDS_OR_NONE}}
- Dependency readiness: {{DEP_TABLE_OR_BULLETS}}
- Architect verdict / role: {{ARCHITECT_VERDICT}} / {{STACK_SPECIALIZATION}}
- Workspace root: {{REPO_ROOT}}

## Child acceptance criteria & out of scope
AC:
{{CHILD_AC_LIST}}

Out of scope:
{{CHILD_OOS}}

## Strategy v2 (source of truth for technical alignment)
{{FULL_STRATEGY_V2_MARKDOWN}}

## Current-state findings (from planner)
{{PATH_BULLETS}}

## Monorepo constraints
- Child = deliverable boundary; epic = context only.
- Model owns domain; API = auth + schema map + owner scoping; web = UI + TanStack Query + BFF cookies.
- B0 Docker Postgres default acceptance.
- Prefer concrete paths/names from Strategy v2; label assumptions.
- No secrets, tokens, or credentialed URLs.

## Required work
1. If go/no-go is NO-GO or Strategy is missing/unsound, return BLOCKED with reason — do not fabricate a full child WBS.
2. Produce a roadmap-like plan: phases/milestones, then ordered tasks T1..Tn.
3. Map every child AC to tasks + DoD evidence; map each Strategy S# to at least one task or an explicit deferral.
4. Fold the risk register: mitigate→T#; open_question→Human decisions; accept→residual.
5. Stay in-child scope; name deferred sibling PPT work explicitly.
6. Follow the output format below (align with plan-issue reference action-plan sections).

## Output format (mandatory)

# PM/BA action plan

**Verdict:** READY_FOR_SME_AUDIT | READY_WITH_HOLDS | BLOCKED
**Author role:** Product Manager / BA engineer (subagent)

## Roadmap
| Phase | Milestone | Outcome | Exit criteria |
| ----- | --------- | ------- | ------------- |
| P0 | … | … | … |
| P1 | … | … | … |

## Go / no-go (echo)
**Verdict:** {{echo}}
**Holds:** …

## 1. Objective
…

## 2. Prerequisites / blockers
…

## 3. Current-state findings
(reuse/refine planner bullets; cite paths)

## 4. Target design
(align to Strategy v2 — do not redesign)

## 5. Risk register & human decisions
| ID | Risk | Disposition | Mitigation / question / accept | Owner |
| -- | ---- | ----------- | ------------------------------ | ----- |
| R# | … | … | … | T# / Human |

### Human decisions
| ID | Question | Options / default | Needed by |
| -- | -------- | ----------------- | --------- |
| R# | … | … | before T# |

## 6. Work breakdown
| Task | Phase | Work | Files / surface | AC / S# | Size | Risks |
| ---- | ----- | ---- | --------------- | ------- | ---- | ----- |
| T1 | P0 | … | `…` | AC1, S1 | S/M/L | R1 |

## 7. Test plan
…

## 8. Definition of done
| AC | Evidence |
| -- | -------- |
| … | … |

## 9. Downstream handoff
(what Blocks consumers need)

## Notes for planner
- Short bullets; flag any place Strategy was ambiguous.
```

## Parent: interpreting results

| Verdict               | Parent action                                                                     |
| --------------------- | --------------------------------------------------------------------------------- |
| `READY_FOR_SME_AUDIT` | Light merge → SME audit                                                           |
| `READY_WITH_HOLDS`    | Keep holds visible; merge → SME audit (or resolve trivial holds first)            |
| `BLOCKED`             | Do not claim a full plan; fix strategy/deps or switch to NO-GO / blocker planning |

If PM/BA proposes layering that contradicts Strategy v2 / Architect, reject in light merge or convert to `open_question` — do not silently accept a re-architecture.
