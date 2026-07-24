---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024 / #11 PR #104 babysit: `__meta__` unit tests for Codecov patch coverage
  (importlib.metadata + pyproject fallback paths)

### Next action

- Land PR #104 when CI green; configure Trusted Publishers; first live publish
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR writes modules/model/CHANGELOG.md only (not root CHANGELOG.md)
