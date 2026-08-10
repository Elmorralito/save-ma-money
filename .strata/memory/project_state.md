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

- **PPT-070 / #163:** epic closed — in-app payment dues delivered (children #164–#168;
  PRs [#197](https://github.com/Elmorralito/save-ma-money/pull/197)–[#207](https://github.com/Elmorralito/save-ma-money/pull/207)).
  Index: [`docs/issues/README.md` Part VIII](../../docs/issues/README.md#part-viii--ppt-070-payment-due-date-reminders-163).
- **PPT-075 / #168:** docs/OpenAPI/B0 close-out ([PR #207](https://github.com/Elmorralito/save-ma-money/pull/207)).
- **PPT-074 / #167:** SPA dues + Due soon ([PR #206](https://github.com/Elmorralito/save-ma-money/pull/206)).
- **PPT-073 / #166:** `/transaction-templates` API ([PR #205](https://github.com/Elmorralito/save-ma-money/pull/205)).
- **PPT-072 / #165** · **PPT-071 / #164:** model services + schema.

### Last completed (this session) — ops

- **PPT-067 publish-dev path gate** landed (#194). Closed Node 25 Dependabot #192 (stay on 22).
- **PPT-066 / #131** — `py-model-v*` cutover (PSR `tag_format` + dual-trigger publish; SSOT
  [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066)).

### In progress (ACTIVE)

- None for PPT-070. Optional follow-up: SQLModel CHECK metadata drift so Migration Check
  can run without `skip-migrations` (unrelated to dues epic MVP).

### Open (backlog)

- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.
- Alembic/`alembic check` SQLModel CHECK alignment (`chk_financing_share`, etc.).

### Next action

- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
