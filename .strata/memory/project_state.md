---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024 / #11: model packaging + python-semantic-release
  (`modules/model/CHANGELOG.md` only; root CHANGELOG stays auto-updates.yml)
  - publish-model.yml on model-v\* tags

### Next action

- Land PPT-024 PR; configure Trusted Publishers; first feat(model) merge → tag → PyPI
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR must not write root CHANGELOG.md
