---
name: Child issue (under epic)
about: Epic sub-issue with step order, tight tasks, and sibling blockers (e.g. PPT-034 / #45 under #42).
title: "feat/PPT-0NN: [domain] Title in sentence case"
labels: ["enhancement"]
---

<!--
Title: {semantic}/PPT-{NNN}: [{domain}] {Sentence case}
Must link Parent epic. Keep scope to one step in the epic implementation order.
Business logic stays in papita_txnsmodel; API children wire routers/schemas/deps only.
References: #42 children (#43–#50), e.g. #45 scaffold.
-->

**Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) · **Program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) · **Step:** <!-- N --> · **PPT-{NNN}**

## Goal

<!-- Short outcome for this step only (1–3 sentences). -->

## Depends on

- <!-- [PPT-0NN #NN](…) — prerequisite child or gate -->

## Blocks

- <!-- [PPT-0NN #NN](…) — next sibling / parallel track -->

---

## Tasks

### <!-- Area: App / Router / Auth / Tests / Docs -->

- [ ] <!-- Concrete checkbox -->
- [ ] <!-- -->

### Tests / CI

- [ ] <!-- Unit / live B0 coverage for this step -->
- [ ] <!-- No secrets in git -->

## Platform rule (B0 + B1)

- [ ] B0: <!-- Docker Postgres acceptance for this step -->
- [ ] Auth / B1: <!-- if this step touches Auth; else N/A -->

## Out of scope

- <!-- Explicitly deferred to later PPT children or post-MVP -->

## Acceptance criteria

- [ ] <!-- Matches epic step / mapping doc for this PPT -->
- [ ] <!-- OpenAPI / tenant / health contracts unchanged unless this step owns them -->

## References

- Parent epic: <!-- #42 -->
- <!-- Mapping / design docs / code paths this step touches -->
