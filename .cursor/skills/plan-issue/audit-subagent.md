# plan-issue — audit subagent

## Possibility

Yes. Cursor’s `Task` tool can run a **separate agent** that did not author the plan. Use `subagent_type: generalPurpose` with an explicit **Expert SME / technical expert** role. There is no dedicated “auditor” agent type; role + checklist in the prompt is the supported pattern.

**Not suitable:** `bugbot` / `security-review` (fixed single-shot prompts), `explore` alone (too shallow for A–N + risk carry-through), parent self-check as the _only_ audit (lacks independent review).

## Parent: how to invoke

1. Finish Strategy v2 + action plan (or NO-GO stub). **Do not** show the human yet.
2. Read this file and the A–N table in [reference.md](reference.md).
3. Call `Task` with:
   - `subagent_type`: `generalPurpose`
   - `model`: `inherit` (unless the user named an allowed model)
   - `description`: `SME plan audit` (or similar, ≤5 words, distinct)
   - `run_in_background`: `false` (must block until the audit returns)
   - `prompt`: fill the template below (include full draft plan + issue/epic ids + dependency table)
4. Apply findings (fix draft). Optionally re-invoke **once** after fixes.
5. Present to human with `Audit: PASS` / `PASS WITH HOLDS` and note that audit was via subagent.

Parent may spot-check repo paths the auditor flags, but must **not** skip the subagent or rewrite the auditor’s fail list away without fixing the draft.

## Subagent prompt template

Copy into the `Task` `prompt` parameter. Replace `{{…}}` placeholders.

```text
You are an Expert subject-matter expert and technical expert for the save-ma-money monorepo (papita_txnsmodel / papita_txnsapi / @papita/web).

Role: independent pre-presentation auditor. You did NOT write the plan. Your job is to find gaps, false readiness, layering violations, weak risks, and human-unreadiness — not to rewrite the plan or implement code.

## Context
- Child issue: {{CHILD_ISSUE_URL_OR_NUMBER}} ({{CHILD_TITLE}})
- Parent epic: {{EPIC_URL_OR_NUMBER}} ({{EPIC_TITLE}})
- Go/no-go claimed by planner: {{GO|GO_WITH_HOLDS|NO_GO}}
- Workspace root: {{REPO_ROOT}}

## Draft under audit
{{FULL_DRAFT_PLAN_MARKDOWN}}

## Repo constraints (enforce)
- Child = deliverable boundary; epic = context only.
- API: routers = auth + schema map + owner scoping; business logic only in papita_txnsmodel.
- Web: UI + TanStack Query + BFF cookies; no TS domain logic.
- Model: schema papita_transactions; soft delete active/deleted_at.
- B0 Docker Postgres is default acceptance; do not treat Supabase PG/pooler as the gate.
- Prefer evidence from issue bodies + repo over assumptions.

## Required work
1. Optionally verify contested dependency claims with gh issue view and quick repo inspection (cite paths). Do not implement features.
2. Score checklist A–N (see below). For each item: PASS or FAIL with one concrete reason and a suggested fix.
3. Especially stress-test: dependency readiness honesty, risk register dispositions, risk→task / open_question→Human decisions carry-through, layering, tenancy.
4. Return ONLY the audit report format below — no rewritten full plan.

## Checklist A–N
A Verdict integrity — go/no-go matches dependency table; no fake ready
B Scope lock — tasks in-child only (unless NO-GO redirect)
C AC coverage — each child AC → task + DoD evidence
D Dep contracts — only existing/held services/schemas
E Layering — no business logic in API/web
F Tenancy/auth — owner scoping where data is exposed
G Tests & B0 — non-empty; deferrals named by PPT/issue
H Concrete paths — routes/files/methods cited
I Assumptions — labeled; not silent facts
J Secrets — none in draft
K Iteration trace — v2 fixes reflected in final plan
L Risk register — every risk has mitigate | open_question | accept
M Risk → action — mitigations→tasks; open questions→Human decisions
N Human-ready — verdict, questions, residual risks, first task obvious

## Output format (mandatory)

# SME technical audit

**Verdict:** PASS | PASS WITH HOLDS | FAIL
**Auditor role:** Expert SME / technical expert (subagent)

## Checklist
| ID | Result | Finding | Suggested fix |
| -- | ------ | ------- | ------------- |
| A | PASS/FAIL | … | … |
| … | … | … | … |
| N | PASS/FAIL | … | … |

## Critical blockers
- … (empty if none)

## Audit holds (human decisions needed)
- … (empty if none)

## Residual notes for planner
- Short bullets only; do not paste a new full plan.
```

## Parent: interpreting results

| Subagent verdict  | Parent action                                                                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PASS`            | Present draft; `Audit: PASS` (via SME subagent)                                                                                                                          |
| `PASS WITH HOLDS` | Present draft + holds; or fix holds if trivial, then present                                                                                                             |
| `FAIL`            | Apply suggested fixes; re-invoke subagent **once** with revised draft; if still FAIL → present with `Audit: PASS WITH HOLDS` listing remaining fails (do not claim PASS) |

If `Task` / subagent is unavailable in the environment, fall back to parent self-audit using the same checklist and report format, and state: `Audit: … (parent fallback — subagent unavailable)`.
