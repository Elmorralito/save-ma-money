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

- **PPT-072 / #165:** landed on main ([PR #204](https://github.com/Elmorralito/save-ma-money/pull/204)) —
  upcoming-dues + mark-paid / clear-paid in `papita_txnsmodel`.
- **PPT-071 / #164:** schema + migration for dues columns on `transaction_templates`.
- **PPT-068 / #139**, **PPT-063 / #128**, **PPT-069 / #140**, **PPT-067 / #132**: on main.

### Last completed (this session) — ops

- **PPT-067 publish-dev path gate** landed (#194). Closed Node 25 Dependabot #192 (stay on 22).
- **PPT-066 / #131** — `py-model-v*` cutover (PSR `tag_format` + dual-trigger publish; SSOT
  [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066)).

### In progress (ACTIVE)

- **PPT-073 / #166:** [PR #205](https://github.com/Elmorralito/save-ma-money/pull/205) —
  transaction-templates CRUD + upcoming-dues / mark-paid / clear-paid FastAPI routers;
  restore model path version **1.0.3** (PSR had rewritten to 1.0.1, breaking API `>=1.0.3`);
  CI fix: coerce pandas NaN on optional ints before DTO validate; flatten nested `TableDTO`
  FKs in `_relation_uuid` for mark-paid responses.
- **[PR #193](https://github.com/Elmorralito/save-ma-money/pull/193):** GHA Dependabot bumps +
  e2e login/nav hardening + Hadolint HEALTHCHECK JSON / DL3066 ignore (if still open).

### Open (backlog)

- **PPT-070** children #167–#168 — SPA Due soon + OpenAPI/docs after PPT-073 lands.
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.

### Next action

- Open / merge PR for PPT-073 / #166; then PPT-074 / #167 web dues UI
- Do not re-add closed GH issues into `.strata/issues/`

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
