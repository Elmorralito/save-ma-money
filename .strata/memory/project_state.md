---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024 / #11: model-only packaging — `package.sh --mod model`, publish-model.yml
  (TestPyPI/PyPI OIDC), README/CI docs, `__meta__` uses importlib.metadata

### Next action

- Land PPT-024 PR; configure Trusted Publishers; first TestPyPI dispatch / model-v\* tag
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- Model publish: tag `model-v*` → PyPI; dispatch → TestPyPI (or confirmed PyPI)
