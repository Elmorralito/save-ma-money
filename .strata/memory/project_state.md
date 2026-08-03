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
  error chip, BFF logout → `/login`. Vitest green. PR [#152](https://github.com/Elmorralito/save-ma-money/pull/152).
  Strata live item `20260803-06` until merge + GitHub close.
- **PPT-059 / #124:** BFF durability contract + fail-closed runtime — merged via
  [#153](https://github.com/Elmorralito/save-ma-money/pull/153); strata item deleted.
- **PPT-061 / #126:** E2E seed fixtures merged (PR #151). Handoff: #121 `globalSetup`.
- **PPT-060 / #125:** Auth edge-case MVP matrix locked in web README.
- **Closed on GitHub (no strata item):** #48, #50, #89, #117–#120, #124–#126 — see
  GitHub / learnings (`web-forms-ux-kit`, `web-ledger-ui-no-domain`, etc.).

### Next action

- Merge PPT-062 PR (#152); close GitHub #127; drop strata item `20260803-06`
- Next epic children from [#112](https://github.com/Elmorralito/save-ma-money/issues/112)
  when starting work (e.g. #121 Playwright, #139 email verify) — capture then
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
