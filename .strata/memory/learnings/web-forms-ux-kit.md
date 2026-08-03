---
name: web-forms-ux-kit
description: Use modules/web/src/forms/ Zod+RHF kit for feature forms; toast vs inline by error class.
---

# Web forms UX kit (PPT-055)

When adding or changing SPA forms under `modules/web`:

1. Prefer `zod` + `react-hook-form` + `@hookform/resolvers/zod` via `src/forms/`.
2. Keep OpenAPI payload mapping in `*FormState` → `to*Create/Update` — Zod is UX validation only.
3. On mutation failure call `applyMutationError` (422 fields inline; 429/network/5xx toast + root).
4. Reuse `FormField` / `FormRootError` and `formatMoney` / `formatDate` — do not invent domain rules in TS.
5. Documented SSOT: `modules/web/README.md` § Forms & UX standards.
