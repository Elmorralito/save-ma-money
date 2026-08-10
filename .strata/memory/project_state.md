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

- **PPT-073 / #166:** landed on main ([PR #205](https://github.com/Elmorralito/save-ma-money/pull/205)) —
  `/transaction-templates` CRUD + upcoming-dues / mark-paid / clear-paid FastAPI routers.
- **PPT-072 / #165:** upcoming-dues + mark-paid / clear-paid in `papita_txnsmodel`
  ([PR #204](https://github.com/Elmorralito/save-ma-money/pull/204)).
- **PPT-071 / #164:** schema + migration for dues columns on `transaction_templates`.
- **PPT-068 / #139**, **PPT-063 / #128**, **PPT-069 / #140**, **PPT-067 / #132**: on main.

### Last completed (this session) — ops

- **PPT-067 publish-dev path gate** landed (#194). Closed Node 25 Dependabot #192 (stay on 22).
- **PPT-066 / #131** — `py-model-v*` cutover (PSR `tag_format` + dual-trigger publish; SSOT
  [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066)).

### In progress (ACTIVE)

- **PPT-074 / #167:** SPA payment dues UI + dashboard **Due soon** — OpenAPI sync, typed
  `transactionTemplates` client/query keys, `/payment-dues` CRUD + mark/clear paid,
  dashboard panel; presentation only over PPT-073 API (branch `feat/PPT-074`).

### Open (backlog)

- **PPT-070** child #168 — tests, OpenAPI sync gate, docs index after PPT-074.
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.

### Next action

- Open / merge PR for PPT-074 / #167; then PPT-075 / #168
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
