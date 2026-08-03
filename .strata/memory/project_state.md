---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-061 / #126:** E2E seed fixtures (strategy A — API HTTP script) on main.
  `make web-e2e-seed` / `pnpm web:seed-e2e` → `modules/web/e2e/.auth/seed.json`.
  Strata id `20260803-05` (handoff to #121 `globalSetup`).
- **PPT-055 / #120:** forms + UX standards — closed/merged; strata item deleted.
- **Strata cleanup:** no `issues/archive/`; closed work → GitHub / git only.
- **PPT-059 / #124:** BFF durability docs + fail-closed runtime; PR
  [#153](https://github.com/Elmorralito/save-ma-money/pull/153) (strata id
  remapped to `20260803-06` after merge conflict with PPT-061's `20260803-05`).
- **PPT-054 / #119:** GH closed by #148 (spending). Carry-forward:
  CF/trends/export/dashboard.

### In progress (ACTIVE)

- **PPT-059 / #124** (`20260803-06`): PR #153 — merge then delete strata item

### Open (backlog)

- **PPT-061 / #126** (`20260803-05`): seed landed; #121 Playwright handoff

### Next action

- Merge PR #153 / close #124; delete strata `20260803-06`
- PPT-056 (#121) Playwright gate — call `make web-e2e-seed` from `globalSetup`
- PPT-054 carry-forward: cash-flow + trends → export + 501 UX → dashboard
- PPT-068 (#139); PPT-057 (#122)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
