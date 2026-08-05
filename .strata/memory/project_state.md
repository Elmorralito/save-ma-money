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
- **PPT-067 / #132:** API GHCR (#188) + web GHCR / Docker Image Security (#190) on main.

### In progress (ACTIVE)

- **[PR #191](https://github.com/Elmorralito/save-ma-money/pull/191):** Dependabot GHA bumps;
  e2e login assert fixed for dashboard "Welcome back, …" h1 race.

### Open (backlog)

- **PPT-070** children #164–#168 — dues schema/services/API/SPA/tests (not started in code).
- **PPT-066 / #131** — language-prefixed git tags (`py-api-v*` aligns with PPT-067 image tags).

### Next action

- Merge PR #191; set `save-ma-money-web` GHCR package visibility if needed
- Start PPT-071 schema when ready for dues
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
