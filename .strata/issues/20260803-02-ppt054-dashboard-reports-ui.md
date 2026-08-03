---
id: 20260803-02
type: feature
status: in-progress
severity: high
area: modules/web
created: 2026-08-03
---

**What:** PPT-054 [#119](https://github.com/Elmorralito/save-ma-money/issues/119) dashboard + reports UI on existing `/api/v1/reports/*` (spending / cash-flow / trends / export), with client-contract window checks and BFF cookie fetches. Presentation only — no TS `ReportService`.

**Why:** Epic PPT-046 Step 2c after accounts context (#117) and ledger UI (#118). Unblocks PPT-056 (#121) E2E report flow. Must honor PPT-044 max window, foreign-account 404, and `refresh_balances` default false.

**Progress (this session):**

- PR1 slice landed in working tree: `lib/reportWindow.ts` (+ tests), `api/reports.ts` (`getSpendingReport`), query keys/options, `ReportFilters` + `SpendingReportView`, `ReportsPage` spending UI, friendly `formatApiError` for `report_window_too_large` / `report_account_not_found`.
- Rebased onto main with PPT-053 ledger UI present; strata id `20260803-02` (avoids clash with archived PPT-053 `20260803-01`).
- `pnpm run web:test` / `web:lint` green (48 tests).

**Still open on #119:**

- Cash-flow + trends tabs
- Export download path + budget-performance 501 UX
- Dashboard compose (balances summary + recent activity via `GET /transactions` from #118)

**Resolution:** (open)
