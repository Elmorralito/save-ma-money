# plan-issue — reference

## Risk register (Strategy → action plan)

Create during **Strategy v1**, refine in **v2**, copy into the action plan. Every row needs a disposition.

```markdown
### Risk register

| ID  | Risk | Impact | Disposition                         | Mitigation / open question / accept note | Owner (task or human) |
| --- | ---- | ------ | ----------------------------------- | ---------------------------------------- | --------------------- |
| R1  | …    | H/M/L  | mitigate \| open_question \| accept | …                                        | T3 / Human before T1  |
```

**Rules**

- `mitigate` → owner is a work-breakdown task id (`T#`) that implements the mitigation.
- `open_question` → owner is **Human**; state when it must be answered (e.g. before T1, before merge).
- `accept` → note residual impact + deferral PPT/issue if deferred.
- Do not drop Strategy risks when writing the action plan; only reclassify with a reason.

## Detailed action-plan template

**Author:** PM/BA subagent ([pm-ba-subagent.md](pm-ba-subagent.md)), then parent light merge. Use when go/no-go is **GO** or **GO WITH HOLDS**.

```markdown
# Plan: {semantic}/PPT-{NNN} — #{issue}

## Go / no-go

**Verdict:** GO | GO WITH HOLDS | NO-GO
**Child:** #{n} · **Epic:** #{e}

### Dependency readiness

| Dep | PPT     | Issue state | Repo evidence | Status                        |
| --- | ------- | ----------- | ------------- | ----------------------------- |
| …   | PPT-0xx | OPEN/CLOSED | `path/…`      | ready/partial/blocked/unknown |

**Holds (if any):** …

## Roadmap (PM/BA)

| Phase | Milestone | Outcome | Exit criteria |
| ----- | --------- | ------- | ------------- |
| P0    | …         | …       | …             |

**PM/BA verdict:** READY_FOR_SME_AUDIT | READY_WITH_HOLDS
**Author:** Product Manager / BA engineer (Task generalPurpose)

## 1. Objective

One paragraph: problem → outcome for this PPT.

## 2. Prerequisites / blockers

Checklist; stop conditions if a dep regresses.

## 3. Current-state findings

Bullets with file paths.

## 4. Target design

- Surface (routes/schemas **or** model tables/services **or** web screens)
- Service / layer calls and ownership rules
- Error → HTTP (or UI) mapping when relevant
- OpenAPI / docs impact for **this** step vs deferred siblings

## 4b. Architect review (Strategy gate)

**Verdict:** SOUND | SOUND WITH GAPS | UNSOUND | BLOCKED: missing stack
**Architect role:** {stack specialization} (Task generalPurpose)
**Strategy points:** S# validation summarized or linked from architect report

## 5. Risk register & human decisions

(Paste Strategy v2 register, including Architect risk addenda; PM/BA may refine owners.)

### Human decisions (from `open_question` rows)

| ID  | Question | Options / default | Needed by |
| --- | -------- | ----------------- | --------- |
| R#  | …        | …                 | before T# |

### Residual (`accept`)

- R#: … (deferred to #… / PPT-… if any)

## 6. Work breakdown (action plan)

Ordered tasks by roadmap phase: files · AC/`S#` · complexity (S/M/L) · linked `R#`.

| Task | Phase | Work | Files | AC / S# | Size  | Risks addressed |
| ---- | ----- | ---- | ----- | ------- | ----- | --------------- |
| T1   | P0    | …    | `…`   | …       | S/M/L | R1              |

## 7. Test plan

Unit/API/e2e as appropriate; B0 how-to; what is deferred to a later PPT; tests that cover `mitigate` risks.

## 8. Definition of done

Map each child acceptance criterion → concrete evidence (tests, endpoints, migrations).
Confirm each `mitigate` risk has evidence or an explicit residual note.

## 9. Downstream handoff

What **Blocks** consumers need (stable contracts, OpenAPI fields, fixtures).

## 10. Pre-presentation audit

**Result:** PASS | PASS WITH HOLDS
**Auditor:** SME/technical-expert subagent (Task generalPurpose)
**Holds (if any):** …
```

## Pre-presentation audit (detail)

**Required:** run via SME/technical-expert **subagent** — see [audit-subagent.md](audit-subagent.md). Parent must not be the sole auditor. Private revise → subagent audit → (optional one re-audit) → then present.

| ID  | Check             | Fail if                                                                       |
| --- | ----------------- | ----------------------------------------------------------------------------- |
| A   | Verdict integrity | Go/no-go contradicts dependency statuses or invents `ready`                   |
| B   | Scope lock        | Tasks belong to a sibling PPT or epic close-out, not this child               |
| C   | AC coverage       | Any child acceptance criterion lacks a task and DoD evidence line             |
| D   | Dep contracts     | Plan calls missing service/schema/migration without a hold or NO-GO           |
| E   | Layering          | Business rules placed in API routers or TypeScript                            |
| F   | Tenancy / auth    | List/get/mutate endpoints omit owner scoping discussion                       |
| G   | Tests & B0        | No tests, or “test later” without naming the deferral issue                   |
| H   | Concrete paths    | Vague verbs only (“wire up”, “add endpoints”) with no paths/names             |
| I   | Assumptions       | Unlabeled guesses treated as repo facts                                       |
| J   | Secrets           | Any credential, token, or private URL in the draft                            |
| K   | Iteration trace   | Critique fixed something in v2 but final plan still has the old gap           |
| L   | Risk register     | Strategy risks missing, or any risk lacks mitigate / open_question / accept   |
| M   | Risk → action     | `mitigate` not linked to a task; `open_question` missing from Human decisions |
| N   | Human-ready       | Reader cannot tell verdict, open questions, residual risks, or first task     |

**Pass rule:** subagent returns `PASS`, or `PASS WITH HOLDS` / remaining fails listed under **Audit holds** with a human decision needed. Do not claim PASS after a subagent `FAIL`.

## NO-GO stub

```markdown
# Plan blocked: #{child} waiting on #{blocker}

## Go / no-go

**Verdict:** NO-GO

### Dependency readiness

(table as above)

## Why blocked

…

## Risks reinforcing the block

| ID  | Risk | Disposition                          | Note |
| --- | ---- | ------------------------------------ | ---- |
| R1  | …    | open_question \| mitigate on blocker | …    |

## Recommended next step

Plan or implement #{blocker} ({PPT}) first.

## Optional — plan for blocker only

(same action-plan template scoped to the blocker, including its risk register)

## Pre-presentation audit

**Result:** PASS | PASS WITH HOLDS
**Auditor:** SME/technical-expert subagent (Task generalPurpose)
**Holds (if any):** …
```

## Subagent gates (separation)

| Gate      | When                              | Role                          | Produces / validates                 |
| --------- | --------------------------------- | ----------------------------- | ------------------------------------ |
| Architect | After Strategy v1                 | Stack-specialized architect   | Each `S#` + fit → Strategy v2        |
| PM/BA     | After Strategy v2                 | Product Manager / BA engineer | Roadmap + `T#` WBS + AC traceability |
| SME audit | After PM/BA plan (+ parent merge) | Expert SME / technical expert | Checklist A–N + human readiness      |

Details: [architect-subagent.md](architect-subagent.md), [pm-ba-subagent.md](pm-ba-subagent.md), [audit-subagent.md](audit-subagent.md).

## Example trigger

User: `/plan-issue` for https://github.com/Elmorralito/save-ma-money/issues/166
Epic: https://github.com/Elmorralito/save-ma-money/issues/163

Agent: fetch both → verify #165 → Strategy v1 → **Architect** → Strategy v2 → **PM/BA roadmap plan** → parent merge → **SME auditor** → present with all three gate results.
