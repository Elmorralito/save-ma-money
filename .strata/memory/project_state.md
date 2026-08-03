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

- **PPT-062 / #127:** AppLayout session chip + logout — `sessionUserLabel`, pending/
  error chip, BFF logout → `/login`. **Merged** via
  [#152](https://github.com/Elmorralito/save-ma-money/pull/152). Strata item deleted;
  id `20260803-06` reused for PPT-056.
- **PPT-059 / #124:** BFF durability docs + fail-closed runtime — **merged** via
  [#153](https://github.com/Elmorralito/save-ma-money/pull/153). Strata item deleted.
- **PPT-061 / #126:** E2E seed fixtures (strategy A — API HTTP script) on main via
  [#151](https://github.com/Elmorralito/save-ma-money/pull/151).
  `make web-e2e-seed` / `pnpm web:seed-e2e` → `modules/web/e2e/.auth/seed.json`.
  Handoff owned by #121 `globalSetup`.
- **PPT-060 / #125:** Auth edge-case MVP matrix — **merged**.
- **PPT-055 / #120:** forms + UX standards — closed/merged; strata item deleted.
- **Strata cleanup:** no `issues/archive/`; closed work → GitHub / git only.
- **PPT-054 / #119:** GH closed by #148 (spending). Carry-forward:
  CF/trends/export/dashboard.

### In progress (ACTIVE)

- **PPT-064 / #129** (`20260803-07` on `feat/PPT-064`): Breaking-changes client
  guard — shared `evaluateBreakingChangesGuard`, app-root banner, public
  `VITE_PAPITA_BREAKING_CHANGES_ID` (default `ppt-044`).
- **PPT-056 / #121** (`20260803-06` on `test/PPT-056`): Vitest coverage gate in
  `web-ci`; Playwright critical path + axe (`globalSetup` → `make web-e2e-seed`);
  Lighthouse lab budgets (`lighthouserc.cjs`); `web-e2e.yml` nightly/dispatch;
  PR web security checklist; SPA omit empty `initial_value` on create (avoids
  NULL→NaN list poison). Complements merged #125/#126.

### Open (backlog)

_Nothing open in strata._ Capture next epic children from
[#112](https://github.com/Elmorralito/save-ma-money/issues/112) when starting work.

### Docs hygiene (PPT-058 / #123)

Monorepo indexes now point at `modules/web` + PPT-046: root `README.md` (package
table, architecture mermaid/layer, quick-start §4), `docs/issues/README.md`
Part VII, `.cursor/AGENTS.md` + thin `CLAUDE.md`,
`.cursor/rules/gen-custom/project_structure.mdc`. RUM/Sentry marked deferred in
`modules/web/README.md` (lab Lighthouse stays #121). Local patches ready — PR
not opened until asked.

### Next action

- Land PPT-064 (#129) PR on `feat/PPT-064` (guard + tests + README)
- Open PR for PPT-056 (#121); close after `web-ci` + agreed `web-e2e` gate green
- PPT-054 carry-forward: cash-flow + trends → export + 501 UX → dashboard
- PPT-068 (#139); PPT-057 (#122) CSP/nginx
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
