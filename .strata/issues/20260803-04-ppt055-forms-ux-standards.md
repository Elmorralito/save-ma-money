---
id: 20260803-04
type: feature
status: in-progress
priority: medium
area: modules/web
created: 2026-08-03
tags: [PPT-055, web, forms]
---

# PPT-055 / #120 — Forms validation and loading UX standards

## Intent

Ship Zod + RHF kit under `modules/web/src/forms/`, document UX standards, migrate accounts + categories forms. Locked decisions: custom `FormField` (not shadcn Form); toast vs inline by error class; no reports/dashboard files in this change.

## Progress

- [x] Install `zod`, `react-hook-form`, `@hookform/resolvers`
- [x] `mapServerErrors` / `applyMutationError` / `FormField` / schemas
- [x] `formatDate` / `formatDateTime` via Intl
- [x] Migrate `AccountFormDialog` + `CategoryFormDialog`
- [x] README + Vitest for mapper/schemas/dates
- [ ] PR + close GitHub #120

## Notes

Does not touch `components/reports/**` or dashboard (PPT-054 / #119).
Strata id `20260803-04` (avoids clash with archived PPT-060 `20260803-03`).
