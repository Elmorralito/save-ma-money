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

- **PPT-067 / #132:** Stable GHCR publish from **main only**; PR `publish-dev` → `pr-*`/`dev-*`
  (skip `skip-api-image-dev`); web GHCR `save-ma-money-web` (skip `skip-web-image-dev`);
  Environments `ghcr` / `ghcr-dev`; smoke + digest pins.
- **`feat/bff-oauth-buttons` / [PR #169](https://github.com/Elmorralito/save-ma-money/pull/169):**
  BFF Google/GitHub OAuth (`/bff/auth/oauth/*`), SPA buttons, `access_expires_at`,
  redirect allowlist rebuild + IdP error digests (CodeQL), branding, dashboard TTL +
  snapshots, UI polish. Guide: `modules/web/docs/oauth-supabase-setup.md`.

### Open (backlog)

- **PPT-070** children #164–#168 — dues schema/services/API/SPA/tests (not started in code).
- **PPT-066 / #131** — language-prefixed git tags (`py-api-v*` aligns with PPT-067 image tags).

### Next action

- Land PPT-067 (#132) PR; first GHCR publish via `workflow_dispatch` or `py-api-v*` tag;
  set package visibility on GHCR if needed
- Merge PR #169 once CodeQL / CI green; enable IdP providers + redirect URLs per OAuth doc
- Start PPT-071 schema when ready for dues
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
