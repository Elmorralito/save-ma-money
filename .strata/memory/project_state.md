---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024: PSR tagged `model-v1.0.0`; publish blocked by Poetry CLI + API pin `<1.0`

### Next action

- Land package.sh Poetry CLI fix + API model dep `>=1.0.0,<2.0`
- Re-dispatch Publish model package → PyPI (Trusted Publishers)
- Note: GITHUB_TOKEN tag pushes do not cascade to publish-model.yml

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR writes modules/model/CHANGELOG.md only (not root CHANGELOG.md)
