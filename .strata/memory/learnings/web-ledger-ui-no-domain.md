---
trigger: before adding transactions, movements, or bulk create UI in modules/web
applies-when: modules/web/**/transactions*, modules/web/**/movements*, modules/web/src/api/transactions.ts, modules/web/src/api/movements.ts
origin: success
---

**Lesson:** Ledger screens are presentation-only. Call `/api/v1/transactions` and `/api/v1/movements` via thin helpers + `queryOptions`; never invent balance math or transfer double-entry in TypeScript.

- Always send `Idempotency-Key` on txn create/bulk (`api/idempotency.ts`); Redis optional for replay.
- Cap bulk rows with `bulkMaxTransactions(client-contract)` (fallback 100); surface `bulk_too_large`.
- After writes, invalidate txn/movement lists **and** `queryKeys.accounts.lists()` / `details()` (`invalidateAfterLedgerWrite`).
- Movements: Execute/Cancel/Edit only when `status === "pending"`; immediate create uses `scheduled: false`.
- Do not expose `POST .../split` (501 deferred to v4).
