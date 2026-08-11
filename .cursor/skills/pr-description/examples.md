# Example PR description output

Illustrative shape from branch `ops/PPT-039` vs `origin/main`. Use as a
**format and tone** reference — do not copy facts into other PRs.

```markdown
**Branch:** `ops/PPT-039` (tracks `origin/ops/PPT-039`, clean)
**Base:** `origin/main` (`4f8a344…`) · **6 commits** · **~92 files**
**Suggested title:** `feat/PPT-039: [api] Supabase Auth (JWKS, OAuth, tenant link)`

---

## Summary

Reissues **PPT-039 / #49** as **Supabase Auth ownership** (not pooler DB): FastAPI verifies Supabase JWTs, delegates register/login/refresh/logout/OAuth to GoTrue, and links `papita_transactions.users.id` to Auth `sub`. Local HS256 remains **tests-only**. Unifies `PAPITA_ENV` under `environments/` and documents Auth-first MVP.

## Out of scope / Highlights

**Out of scope**

- Requiring Supabase Postgres / transaction pooler for MVP
- CI Supabase secrets hardening (**#50 / PPT-040**)
- Live browser SSO polish beyond unit-test coverage

**Highlights**

- Google/GitHub OAuth (PKCE) + SSO handoff
- Auth health on `/health`, `/health/auth`, `/health/ready`
- Soft-delete-safe provision + optional Admin orphan cleanup

## Changes

**Environments / ops**

- `environments/{local,staging,production}/.env.example`, `environments/README.md`, settings/`PAPITA_ENV` loading
- Compose injects `SUPABASE_*` (incl. service role / OAuth) into the API service
- `bin/bash/auth_smoke.sh`, B1/deploy helpers, untrack generated `docs/coverage.xml`

**Model / migrations**

- Alembic: link users to Auth + `display_name` / `phone` / `provider_type`
- `UsersService.ensure_from_auth_subject` (provision, soft-delete guard, profile refresh)
- `ProviderType` enum (`email` / `google` / `github`)

**API**

- JWKS verify + tenant provision; register/login via supabase-py
- Google/GitHub OAuth (PKCE) + SSO token handoff; orphan Auth cleanup; client cache
- Auth health probe on `/health`, `/health/auth`, `/health/ready`
- Rate limits / cookie Secure / allowlisted `redirect_to`

**Docs / memory**

- `docs/design/ARCHITECTURE.md` Part VI (auth contract), PPT-039 issue write-ups
- Strata learning `supabase-auth-ownership`

**Tests**

- Expanded Auth/Supabase/health/settings coverage; model `ensure_from_auth` cases

<details>
<summary>File changes (~92 files)</summary>
```

environments/local/.env.example
modules/api/src/papita_txnsapi/core/supabase_auth.py
modules/api/src/papita_txnsapi/routers/v1/auth.py
modules/model/alembic/versions/2026_07_13_2220-h5c6d7e8f9a0_link_users_to_supabase_auth.py

# … abbreviated; use full `git diff --stat` in real PRs

```

</details>

## Commits

| Hash | Subject |
|------|---------|
| `255bf82` | feat(api): unify environments and reissue PPT-039 as Supabase Auth |
| `51822cc` | feat(api): verify Supabase Auth JWTs and provision tenants (PPT-039) |
| `7820724` | docs(api): finish PPT-039 Auth contract and auth-smoke entrypoint |
| `ade30ca` | feat(api): register and login via Supabase Auth client |
| `34eabad` | fix(api): pass Supabase Auth env into Compose API |
| `ecb613f` | feat(api): complete Supabase Auth OAuth, profile sync, and hardening (PPT-039) |

*(Tip commit message still carries a local `Draft:` prefix from drafting — strip on squash/edit if desired.)*

## Checks, tests, and validation already done

Observed in development on this branch (not claiming remote CI green — `gh` GraphQL was forbidden here):

- [x] Targeted unit tests passed locally during Auth work (e.g. `test_supabase_auth_client`, `test_auth_supabase`, `test_users` ensure/profile, health Auth paths)
- [x] Pre-commit **pylint** failures on Auth modules fixed (rated 10/10 on those files after refactor)
- [x] Alembic migrate blocker (`ProviderType` / postponed annotations) fixed for Docker migrate
- [x] Earlier Docker/auth-fix smoke against a running stack passed after Desktop was up (ephemeral smoke scripts later removed)
- [ ] Full `pre-commit run --all-files` / GitHub Actions status: **not verified in this pass**
- [ ] Staging/prod migrate + end-to-end OAuth browser flow: **not claimed here**
- [ ] `make auth-smoke` with a real `AUTH_SMOKE_EMAIL`: **optional; needs configured env**

## QA / test plan

- [ ] `./bin/bash/alembic.sh --env local` (B0) applies both new Auth migrations cleanly
- [ ] Register + login with email/password against real Supabase Auth; JWT works on a protected route (`GET /auth/me`)
- [ ] Soft-deleted / inactive Auth-linked user cannot be reactivated via provision
- [ ] Google (and/or GitHub) OAuth: `GET /auth/oauth/{provider}?follow=true` → callback → tokens; PKCE cookies cleared
- [ ] Password login after Google signup does **not** overwrite `provider_type` to `email`
- [ ] Orphan cleanup: provision failure after Auth signup deletes Auth user when service role set (register always; login only if recent)
- [ ] `/health`, `/health/auth`, `/health/ready` reflect Auth up/down; local provider skips Auth as healthy
- [ ] Compose API receives `SUPABASE_URL` / anon / service-role / OAuth redirect env
- [ ] Confirm `environments/**/.env` (secrets) are **not** in the PR
- [ ] CI secrets path deferred to #50 — note any local-only Auth keys in review comments

> [!CAUTION]
> ### Risks
> - Migrations change `users` identity (Auth `sub` alignment + profile columns); run on a backup / disposable DB first.
> - `SUPABASE_SERVICE_ROLE_KEY` enables Admin orphan delete (server-only); misconfiguration skips cleanup and can leave Auth orphans.
> - OAuth `redirect_to` allowlist — only API callback + `SUPABASE_OAUTH_REDIRECT_TO`; mis-set env breaks IdP redirect.
> - Blocks #50 (PPT-040) for CI Auth secrets.

> [!WARNING]
> ### Caveats
> - Email confirm / session null on signup: API may return user without tokens depending on Supabase project settings.
> - Tip commit may include doc/coverage cleanup and docstring-only churn — skim separately from Auth behavior.
> - Pooler DB remains optional ops, not this PR’s acceptance criteria.

## References

- GitHub **#49** (PPT-039) · Epic **#42** (PPT-032) · Program **#28** (PPT-031)
- [`docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49`](docs/issues/README.md#part-iv--ppt-039-supabase-auth-reissue-49)
- [`docs/design/ARCHITECTURE.md` Part VI](docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)
- Auth ownership learning: `.strata/memory/learnings/supabase-auth-ownership.md`
```
