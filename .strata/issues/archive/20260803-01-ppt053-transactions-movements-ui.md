---
id: 20260803-01
type: feature
status: resolved
severity: high
area: modules/web
created: 2026-08-03
---

**What:** PPT-053 [#118](https://github.com/Elmorralito/save-ma-money/issues/118) transactions + movements presentation UI on existing FastAPI v1 (typed client, TanStack Query, BFF cookies).

**Why:** Epic PPT-046 Phase 2 ledger screens after accounts/categories (PPT-052). Unblocks E2E flows (#121) and dashboard/reports UI (#119) dependencies that assume txn/movement UX exists.

**Resolution:** Implemented in `modules/web` — `api/transactions.ts` / `movements.ts` + `idempotency.ts` + `invalidateLedger.ts`; domain aliases; TransactionsPage (list/filters/CRUD/bulk + Idempotency-Key); MovementsPage (create/execute/cancel for pending); `Retry-After` on 429 in `PapitaApiError` / `formatApiError`; no Split button (API 501 deferred); README PPT-053 section. Vitest green (`web-lint` / `web-test` / `web-build`). Presentation only — no TS ports of ledger services.
