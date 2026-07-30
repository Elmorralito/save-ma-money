---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-049 / #115 / PR #141:** BFF HttpOnly `papita_sid` session in API + web auth UI;
  babysit: CI TestClient `AUTH_COOKIE_SECURE=false`, session-id rotate on refresh,
  log digests, `.trivyignore` for stale GHSA on patched `react-router@7.18.2`;
  expanded mocked-Supabase BFF + store tests for `codecov/patch`
- **PPT-047 / #113:** Scaffolded `modules/web` (`@papita/web`) — Vite + React 19 + TS strict,
  pnpm workspace (`pnpm-workspace.yaml`, committed `pnpm-lock.yaml`), ESLint 9 + Prettier +
  Vitest smoke, Vite `/api` → `:8000` proxy, Makefile `web-*`, path-filtered `web-ci.yml`,
  Dependabot npm, Node 22 pins (`.nvmrc` / `.node-version`)
- **PPT-065 / #130:** Locked OpenAPI typegen **strategy B** — committed
  `modules/web/openapi/openapi.json`, `make sync-openapi` / `check-openapi` (offline
  `app.openapi()` via `bin/export_openapi.py`), `make generate-types` / `check-types`,
  `web-ci` type drift gate + `openapi-contract.yml` API↔artifact gate (stale-artifact mitigation)
- **npm Dependabot #136:** Vite 8 / Vitest 4 / ESLint 10 group bump; keep `typescript` on
  `~5.9` (typescript-eslint lacks TS 7); Dependabot ignores TS majors
- Poetry/Python workspace unchanged; web quality via Web CI (not Python pre-commit)
- Strata: map entry for `modules/web` in `.strata/docs/ARCHITECTURE.md`

### Next action

- Land PR #141 (PPT-049) after quality-control + Trivy FS green
- PPT-068 email verification (#139); PPT-069 non-goals guardrail (#140)
- PPT-051 design shell (#116) when auth BFF is merged

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
