---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-052 / #117 (in progress):** Accounts + categories UI in `modules/web` — list/detail,
  controlled form dialogs, `formatMoney`, list “first 100” note, global category 404 →
  read-only; update payloads omit empty optionals; Vitest coverage for create/detail/delete
  - auth register UX
- **Local Supabase auth DX:** `AUTH_AUTO_CONFIRM_EMAIL` (default on for `PAPITA_ENV=local`);
  Admin register (`email_confirm`) avoids SMTP 429; login auto-confirm only when Auth email
  is unconfirmed (`supabase_sign_in_with_optional_auto_confirm`)
- **Ops:** `make api-all` / `make api-all-down`; web error copy points at `api-all` for 502/proxy
- **PPT-051 / #116:** Tailwind v4 + shadcn shell (prior)
- **PPT-049 / #115 / PR #141:** BFF HttpOnly session (merged)

### Next action

- Land [#143](https://github.com/Elmorralito/save-ma-money/pull/143) — also fixes TestPyPI
  publish skip (`publish-model.yml` must gate on `inputs.target`, not `event_name == workflow_call`)
- PPT-055 forms kit (#120); PPT-068 email verification (#139); PPT-069 non-goals (#140)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode) — updated this session
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
