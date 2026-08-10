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
- **PPT-067 / #132:** API (#188) + web (#190) GHCR publish + Docker Image Security on main.

### Last completed (this session) — ops

- **PPT-067 publish-dev path gate** landed (#194). Closed Node 25 Dependabot #192 (stay on 22).
- **PPT-066 / #131** — `py-model-v*` cutover (PSR `tag_format` + dual-trigger publish; SSOT
  [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066)).
  Audit fix: stable `workflow_call` version gate no longer keys off dead
  `event_name == workflow_call`; shared `strip_model_release_tag.sh`.

### In progress (ACTIVE)

- **PPT-072 / #165:** [PR #204](https://github.com/Elmorralito/save-ma-money/pull/204) —
  upcoming-dues + mark-paid / clear-paid; model version **1.0.3**; B0
  `OTHER_ASSET` fixture; fix category `dto_type` kw collision on mark-paid create;
  `skip-migrations` for pre-existing alembic check drift on main.
- **[PR #193](https://github.com/Elmorralito/save-ma-money/pull/193):** GHA Dependabot bumps +
  e2e login/nav hardening + Hadolint HEALTHCHECK JSON / DL3066 ignore.

### Open (backlog)

- **PPT-070** children #166–#168 — API/SPA/tests after PPT-072 lands.
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.

### Next action

- Open PR for PPT-072 / #165; then PPT-073 / #166 API routers
- Merge PR #193; set GHCR package visibility if needed
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
