---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-051 / #116:** Tailwind v4 + shadcn/ui shell in `modules/web` — CSS-variable tokens
  (light + `.dark`), primitives (`ui/*`), `PublicLayout` / `AppLayout`, lazy stub routes
  (dashboard/accounts/categories/transactions/movements/reports), jsx-a11y + layout smoke;
  BFF auth from PPT-049 kept (real session, no mock auth)
- **PPT-049 / #115 / PR #141:** BFF HttpOnly `papita_sid` session in API + web auth UI (merged)
- **PPT-047 / #113 · PPT-065 / #130 · PPT-048 / #114:** web scaffold, OpenAPI strategy B,
  thin HTTP client + TanStack Query (prior)
- Poetry/Python workspace unchanged; web quality via Web CI (not Python pre-commit)

### Next action

- Open/merge PR for PPT-051 (`feat/PPT-051`)
- PPT-052 accounts/categories UI (#117); PPT-055 forms kit (#120) when ready
- PPT-068 email verification (#139); PPT-069 non-goals guardrail (#140)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
