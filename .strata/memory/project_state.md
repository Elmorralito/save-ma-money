---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-053 / #118:** Transactions + movements UI in `modules/web` — typed client
  (`api/transactions.ts`, `api/movements.ts`), `Idempotency-Key` on create/bulk,
  bulk cap via client-contract, Movements create/execute/cancel (pending-only),
  ledger invalidation + account balances, `Retry-After` on 429; no Split button
  (API 501 deferred). Vitest / lint / build green. Strata: archived `20260803-01`,
  learning `web-ledger-ui-no-domain.md`
- **PPT-052 / #117 (in progress toward PR):** Accounts + categories UI + local
  Supabase email-confirm DX (`AUTH_AUTO_CONFIRM_EMAIL`, Admin register)
- **PPT-051 / #116:** Tailwind v4 + shadcn shell (prior)
- **PPT-049 / #115 / PR #141:** BFF HttpOnly session (merged)

### Next action

- Open/land PR for PPT-053 (#118) if not yet filed; keep pairing `.strata/` on commit
- Land [#143](https://github.com/Elmorralito/save-ma-money/pull/143) (PPT-052) — also
  fixes TestPyPI publish skip (`publish-model.yml` must gate on `inputs.target`)
- PPT-054 dashboard/reports UI (#119); PPT-055 forms kit (#120); PPT-056 E2E (#121)

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode) — updated this session
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
- Autopilot (#145): Dependabot npm-web group bump paired here for strata-check strict mode
