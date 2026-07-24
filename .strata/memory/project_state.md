---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024 first release: PSR created `model-v1.0.0` + GH release; publish failed
  because `bin/package.sh` used `python -m poetry` (CLI-only Poetry in CI)

### Next action

- Land package.sh Poetry CLI fix; re-dispatch Publish model package → PyPI
- Ensure PyPI/TestPyPI Trusted Publishers + `pypi`/`testpypi` environments
- Note: GITHUB_TOKEN tag pushes do not cascade to publish-model.yml

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR writes modules/model/CHANGELOG.md only (not root CHANGELOG.md)
