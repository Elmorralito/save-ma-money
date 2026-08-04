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

- **PPT-062 / #127:** AppLayout session chip + logout — merged via #152.
- **PPT-059 / #124:** BFF durability docs + fail-closed runtime — merged via #153.
- **PPT-061 / #126:** E2E seed fixtures — merged via #151.
- **PPT-060 / #125:** Auth edge-case MVP matrix — merged.
- **PPT-055 / #120:** forms + UX standards — closed/merged.
- **Strata cleanup:** no `issues/archive/`; closed work → GitHub / git only.

### In progress (ACTIVE)

- **PPT-057 / #122** (`ops/PPT-057`, PR #158): nginx Compose packaging. Autopilot
  follow-up: `nginxinc/nginx-unprivileged` (non-root / DS-0002), listen 8080,
  Docker DNS runtime upstream resolve, cryptography >=50 (CVE-2026-69247).
- **PPT-056 / #121** / **PPT-064 / #129**: verify merge status on main.

### Open (backlog)

_Nothing open in strata._ Capture next epic children from
[#112](https://github.com/Elmorralito/save-ma-money/issues/112) when starting work.

### Docs hygiene (PPT-058 / #123)

Monorepo indexes point at `modules/web` + PPT-046. RUM/Sentry deferred.

### Next action

- Finish PPT-057 / #122 on `ops/PPT-057`: verify `docker build` + `make web-up` smoke
- Open PR `ops/PPT-057: [web] nginx Compose packaging and prod origins`
- PPT-054 carry-forward: cash-flow + trends → export + 501 UX → dashboard
- PPT-068 (#139); PPT-063 (#128) CSP after nginx lands
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
