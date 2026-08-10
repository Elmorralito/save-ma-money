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

- **PPT-074 / #167:** landed on main ([PR #206](https://github.com/Elmorralito/save-ma-money/pull/206)) —
  SPA payment dues UI + dashboard **Due soon**.
- **PPT-073 / #166:** `/transaction-templates` CRUD + dues FastAPI routers ([PR #205](https://github.com/Elmorralito/save-ma-money/pull/205)).
- **PPT-072 / #165:** upcoming-dues + mark-paid / clear-paid in `papita_txnsmodel`
  ([PR #204](https://github.com/Elmorralito/save-ma-money/pull/204)).
- **PPT-071 / #164:** schema + migration for dues columns on `transaction_templates`.

### Last completed (this session) — ops

- **PPT-067 publish-dev path gate** landed (#194). Closed Node 25 Dependabot #192 (stay on 22).
- **PPT-066 / #131** — `py-model-v*` cutover (PSR `tag_format` + dual-trigger publish; SSOT
  [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066)).

### In progress (ACTIVE)

- **PPT-075 / #168:** docs index + README pointers + OpenAPI verify + B0 live fixture harden
  (`REDIS_ENABLED=false` in `test_transaction_templates_live_db.py`). Index:
  [`docs/issues/README.md` Part VIII](../../docs/issues/README.md#part-viii--ppt-070-payment-due-date-reminders-163).

### Open (backlog)

- **PPT-070 / #163** epic close-out after #168 merges.
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.

### Next action

- Merge PPT-075 / #168; then tick / close epic PPT-070 / #163
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
