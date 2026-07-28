---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- **PPT-047 / #113:** Scaffolded `modules/web` (`@papita/web`) — Vite + React 19 + TS strict,
  pnpm workspace (`pnpm-workspace.yaml`, committed `pnpm-lock.yaml`), ESLint 9 + Prettier +
  Vitest smoke, Vite `/api` → `:8000` proxy, Makefile `web-*`, path-filtered `web-ci.yml`,
  Dependabot npm, Node 22 pins (`.nvmrc` / `.node-version`)
- **PPT-065 / #130:** Locked OpenAPI typegen **strategy B** — committed
  `modules/web/openapi/openapi.json`, `make sync-openapi` / `check-openapi` (offline
  `app.openapi()` via `bin/export_openapi.py`), `make generate-types` / `check-types`,
  `web-ci` type drift gate + `openapi-contract.yml` API↔artifact gate (stale-artifact mitigation)
- Poetry/Python workspace unchanged; web quality via Web CI (not Python pre-commit)
- Strata: map entry for `modules/web` in `.strata/docs/ARCHITECTURE.md`

### Next action

- PPT-048 OpenAPI client (#114) on top of locked typegen; and/or PPT-051 design shell (#116)
- Docs indexes for web (root README / `docs/issues`) → PPT-058 / #123

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
