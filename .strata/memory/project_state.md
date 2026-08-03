---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-060 / #125:** Auth edge-case MVP matrix — web README matrix + Playwright
  assumptions; API Auth cross-link; `formatApiError` confirm-email remap; Login/
  Register 429 page tests. Strata archived `20260803-03`. Password reset deferred;
  email-confirm product UX remains PPT-068 (#139).
- **PPT-054 / #119 / PR #148:** Dashboard + reports UI merged on `main`
- **PPT-053 / #118 post-merge audit:** AC→artifact map confirmed (shipped `#147` /
  `2d3e309`); `make web-lint|test|build` green; B0 ledger via BFF+Vite proxy;
  `modules/web/README.md` routes/out-of-scope no longer call dashboard/reports stubs
- **PPT-053 / #118 / PR #147:** Transactions + movements UI — typed client,
  Idempotency-Key, bulk cap, movements execute/cancel, Retry-After on 429; strata
  archived `20260803-01` + learning `web-ledger-ui-no-domain.md`
- **PPT-052 / #117:** Closed — accounts/categories UI + local auth DX via PR #143
- **CodeQL JS/TS + web pre-commit:** Independent `codeql-javascript.yml`; local
  `web-eslint` / `web-prettier` / `web-tsc` / `web-vitest-related` via
  `.github/scripts/pre_commit_web.sh`
- **PPT-051 / #116 · PPT-049 / #115 · PPT-048 / #114:** Prior web epic foundations (merged)

### Next action

- PPT-056 (#121) E2E (use PPT-060 confirmed-user assumptions; incl. ledger + report
  flows); PPT-055 forms (#120); PPT-068 (#139) check-email/resend; PPT-069 (#140)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode) — PPT-060 paired
  (`project_state`, archive `20260803-03`)
- Unrelated WIP left unstaged: `modules/web/src/forms/`, `formatDate.ts` (likely #120)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
