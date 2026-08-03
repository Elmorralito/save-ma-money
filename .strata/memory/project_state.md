---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-055 / #120:** forms + UX standards — closed/merged; strata item deleted.
- **Strata cleanup:** no `issues/archive/`; closed work → GitHub / git only.
- **PPT-059 / #124:** BFF durability docs + fail-closed runtime shipped; PR
  [#153](https://github.com/Elmorralito/save-ma-money/pull/153) opened (`66de473`).
- **PPT-054 / #119:** GH closed by #148 (spending). Carry-forward below:
  CF/trends/export/dashboard.

### In progress (ACTIVE)

- **PPT-059 / #124** (`20260803-05`): PR #153 open — merge then delete strata item

### Next action

- Merge PR #153 / close #124; delete strata `20260803-05`
- PPT-054 carry-forward: cash-flow + trends tabs → export + 501 UX → dashboard compose
- Then PPT-056 (#121) E2E; PPT-068 (#139); PPT-057 (#122)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
