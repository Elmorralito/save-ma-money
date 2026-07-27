---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- Model release automation: PR → TestPyPI `.dev{run_id}` after checks; merge → PSR + `workflow_call` PyPI
- Scripts: `wait_for_pr_checks.sh`, `stamp_model_dev_version.py`; workflows `publish-model-dev.yml` + reusable publish
- Docs: `modules/model/README.md` + `.github/CI.md` release/TestPyPI sections

### Next action

- Confirm GitHub Environment `testpypi` allows PR-branch deployments (Trusted Publisher already on `publish-model.yml`)
- Avoid `[skip ci]` inside squash-merge bodies (skips release-model.yml)

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml

- Prettier-format modules/model/CHANGELOG.md (unblocks Dependabot QC)
