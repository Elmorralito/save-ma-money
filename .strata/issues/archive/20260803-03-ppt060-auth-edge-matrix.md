---
id: 20260803-03
type: feature
status: resolved
severity: med
area: modules/web
created: 2026-08-03
---

**What:** PPT-060 [#125](https://github.com/Elmorralito/save-ma-money/issues/125) Supabase auth edge-case MVP matrix for BFF — document MVP vs deferred, thin SPA error remaps, prove auth 429 is not silent.

**Why:** Locks confirmation/reset decisions for operators and Playwright (#121); keeps product email-confirm UX in PPT-068 [#139](https://github.com/Elmorralito/save-ma-money/issues/139) without expanding SSO/reset scope.

**Resolution:** Published matrix + Playwright assumptions in `modules/web/README.md`; API Auth section cross-link; `formatApiError` remaps `"Email not confirmed"`; Login/Register page Vitest for 429 (+ confirm on login). Password reset / magic link / OAuth SPA deferred explicitly. No new BFF routes.
