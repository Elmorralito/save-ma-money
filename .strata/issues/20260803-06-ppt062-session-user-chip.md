---
id: 20260803-06
type: feature
status: in-progress
severity: low
area: modules/web
created: 2026-08-03
---

**What:** PPT-062 [#127](https://github.com/Elmorralito/save-ma-money/issues/127) minimal session user chip + logout in `AppLayout`.

**Why:** Authenticated shell should show who is signed in and clear the BFF cookie session without a profile/settings product.

**Progress**

- Chip: `sessionUserLabel` (`display_name` → `username` → `email`); pending/error affordances
- Logout via BFF → `removeQueries` + `/login`
- Vitest coverage; PR [#152](https://github.com/Elmorralito/save-ma-money/pull/152)

**Done when:** PR merged and GitHub #127 closed.
