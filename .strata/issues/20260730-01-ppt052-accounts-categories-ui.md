---
id: 20260730-01
type: feature
status: in-progress
severity: high
area: modules/web
created: 2026-07-30
---

**What:** PPT-052 [#117](https://github.com/Elmorralito/save-ma-money/issues/117) accounts + categories presentation UI (list/detail/CRUD dialogs, global-seed read-only mapping) plus local auth DX so BFF register/login works with Supabase Confirm-email / SMTP limits.

**Why:** Unblocks epic PPT-046 feature screens after the design shell (PPT-051). Auth DX is required for local smoke of those screens against Compose + hosted Auth.

**Resolution:** (open) Implementation in `modules/web` + `AUTH_AUTO_CONFIRM_EMAIL` / Admin register path in `modules/api`; expand tests and docs before PR split (UI vs auth).
