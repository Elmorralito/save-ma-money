---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-054 / #119 (in progress):** Dashboard + reports UI — PR1 spending slice in
  `modules/web`: `lib/reportWindow.ts` (mirrors API window delta), `api/reports.ts`,
  `ReportFilters` + `SpendingReportView`, `ReportsPage` (stub replaced), error-code
  copy for `report_window_too_large` / `report_account_not_found`. Vitest + lint green.
- **PPT-053 / #118 / PR #147:** Transactions + movements UI — typed client,
  Idempotency-Key, bulk cap, movements execute/cancel, Retry-After on 429; strata
  archived `20260803-01` + learning `web-ledger-ui-no-domain.md`
- **PPT-052 / #117:** Closed — accounts/categories UI + local auth DX via PR #143
- **CodeQL JS/TS + web pre-commit:** Independent `codeql-javascript.yml`; local
  `web-eslint` / `web-prettier` / `web-tsc` / `web-vitest-related` via
  `.github/scripts/pre_commit_web.sh`
- **PPT-051 / #116 · PPT-049 / #115 · PPT-048 / #114:** Prior web epic foundations (merged)

### Next action

- Finish #119: cash-flow + trends tabs → export download + 501 UX → dashboard compose
  (balances from `listAccounts`; recent activity via `GET /transactions` from #118)
- Then PPT-056 (#121) E2E report flow; PPT-055 forms (#120); PPT-068 (#139); PPT-069 (#140)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode) — updated this session
  (`project_state`, issue `20260803-02`, resolve `20260730-01`, ARCHITECTURE web note)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml

- Autopilot: prettier-formatted CHANGELOG.md after merge of main into feat/PPT-054 (#148)
