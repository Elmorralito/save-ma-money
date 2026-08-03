---
id: 20260730-01
type: feature
status: resolved
severity: high
area: modules/web
created: 2026-07-30
---

**What:** PPT-052 [#117](https://github.com/Elmorralito/save-ma-money/issues/117) accounts + categories presentation UI (list/detail/CRUD dialogs, global-seed read-only mapping) plus local auth DX so BFF register/login works with Supabase Confirm-email / SMTP limits.

**Why:** Unblocks epic PPT-046 feature screens after the design shell (PPT-051). Auth DX is required for local smoke of those screens against Compose + hosted Auth.

**Resolution:** Shipped via [#143](https://github.com/Elmorralito/save-ma-money/pull/143); GitHub issue #117 closed. Accounts/categories UI + local `AUTH_AUTO_CONFIRM_EMAIL` / Admin register DX. Follow-on reports work is PPT-054 [#119](https://github.com/Elmorralito/save-ma-money/issues/119) (`20260803-02`).
