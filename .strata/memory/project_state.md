---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

**Strata issues policy:** do **not** keep closed GitHub issues under `.strata/issues/`
(including `archive/`) — they add agent context noise. History lives on GitHub / git.
Capture with `/strata:capture` only for work in flight.

### Last completed (this session)

- **PPT-068 / #139**, **PPT-063 / #128**, **PPT-069 / #140**: landed on main (see git log).
- **PPT-070 / #163** filed: payment due-date reminders epic + children #164–#168 (issues only).

### In progress (ACTIVE)

- **`feat/bff-oauth-buttons`:** BFF Google/GitHub OAuth (`/bff/auth/oauth/*`), SPA buttons,
  `access_expires_at` on BFF session, redirect allowlist hardening, branding, dashboard
  TTL + accounts/pending snapshots, UI polish. Operator guide:
  `modules/web/docs/oauth-supabase-setup.md`.

### Open (backlog)

- **PPT-070** children #164–#168 — dues schema/services/API/SPA/tests (not started in code).

### Next action

- Land BFF OAuth PR; enable IdP providers + redirect URLs per web OAuth setup doc
- Start PPT-071 schema when ready for dues
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
