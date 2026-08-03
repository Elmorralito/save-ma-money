---
name: Program issue (PPT)
about: Standalone or post-MVP PPT issue with full body (e.g. PPT-042 / #52, PPT-044 / #89, PPT-045 / #93).
title: "feat/PPT-0NN: [domain] Title in sentence case"
labels: ["enhancement"]
---

<!--
Title: {semantic}/PPT-{NNN}: [{domain}] {Sentence case}
  semantic: feat | fix | ops | ci | docs | test | chore | refactor
  domain: [api] | [model] | [infra] | [EPIC][api] only on epics
Labels: durable domain labels; if parent epic is set, apply that epic’s `EPIC: PPT-*` (do not create a new epic track label).
References: #52 (CI badge), #89 (hardening), #93 (uvicorn packaging).
-->

**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-{NNN}** · **Step:** <!-- N or phase name -->

## Summary

<!-- One paragraph: what, why, scope boundary. -->

## Current state (inspected)

| Surface          | Today                      |
| ---------------- | -------------------------- |
| <!-- surface --> | <!-- what exists today --> |

<!-- Optional: credit “Already done” / “Known gaps” tables like #89. -->

## Depends on

- <!-- [#NN](…) (PPT-0NN) — reason -->

## Blocks

- <!-- What this unblocks (DX, follow-on issues, safer ops) -->

## Platform rule (B0 + B1)

<!-- Default for model/API data work: validate Docker Postgres (B0). Auth-only Supabase unless this issue needs pooler. Infra-only may say N/A. -->

Validate on **B0 Docker Postgres** <!-- and optional B1 / Auth --> before closing.

## Decisions to lock in this issue

1. <!-- Decision -->
2. <!-- Decision -->

## Tasks / deliverables

### <!-- Layer: Ops / API / Docs / CI -->

- [ ] <!-- Concrete, testable deliverable -->
- [ ] <!-- -->

### Docs

- [ ] <!-- README / env / ops note updates -->

## <!-- Domain --> integration

- [ ] B0 acceptance <!-- or N/A -->
- [ ] B1 / Auth acceptance <!-- or N/A -->
- [ ] Env vars / docs updated (`.env.example`, README) — **no secrets committed**

## Requirements traceability

| ID                      | Scope    |
| ----------------------- | -------- |
| <!-- FR-NN / NFR-NN --> | <!-- --> |

## Out of scope

- <!-- Bullet list — prevents scope creep -->

## Acceptance criteria

- [ ] <!-- Measurable done condition -->
- [ ] <!-- -->

## References

- <!-- Code paths, design docs, parent epic, related PPT issues -->
