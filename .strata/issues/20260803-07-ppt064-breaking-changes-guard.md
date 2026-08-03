---
id: 20260803-07
type: feature
status: in-progress
severity: med
area: modules/web
created: 2026-08-03
---

# PPT-064 / #129 Client guard for Papita breaking-changes contract

**What:** Shared SPA guard that compares `VITE_PAPITA_BREAKING_CHANGES_ID` (default
`ppt-044`) against `GET /api/v1/meta/client-contract` / `X-Papita-Breaking-Changes`,
with DEV console.error + prod console.warn and a non-blocking banner on mismatch.

**Why:** Epic #112 child — fail loudly (dev) / degrade safely (prod) when PPT-044
discovery drifts; features must not ad-hoc-read discovery headers.

**Acceptance pointers:** `modules/web/src/api/contract.ts` helpers + unit tests;
`BreakingChangesGuard` at app root; README § Breaking-changes guard; public
`VITE_PAPITA_BREAKING_CHANGES_ID` only.
