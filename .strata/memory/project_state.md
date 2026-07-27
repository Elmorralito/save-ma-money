---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-024: model **1.0.1** on PyPI/TestPyPI; model README install/release refresh
- Added `branch-sync.yml` + `branch_sync_check.sh` (fail PRs behind `origin/main`)
- publish-model: bump artifact actions to Node.js 24 (`upload@v6`, `download@v7`)

### Next action

- Prefer dispatch publish when GITHUB_TOKEN tags do not cascade
- Avoid `[skip ci]` inside squash-merge bodies (skips release-model.yml)

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml

- Prettier-format modules/model/CHANGELOG.md (unblocks Dependabot QC)
