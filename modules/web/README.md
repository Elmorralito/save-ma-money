# `@papita/web`

React + TypeScript SPA for the Papita finance client (epic [PPT-046 / #112](https://github.com/Elmorralito/save-ma-money/issues/112)).

This package is presentation-only. Domain rules stay in `papita_txnsmodel` behind `papita_txnsapi` — do not reimplement business logic here.

## Domain boundary (PPT-069 / #140)

**Web must not port domain services.** Accounts, categories, transactions, movements, and reports UI call existing API routes only. The SPA must **never** reimplement `UsersService`, password policy, ledger math, or tenant-ownership rules in TypeScript. Thin OpenAPI types + TanStack Query HTTP mapping is allowed. Epic SSOT: [#112](https://github.com/Elmorralito/save-ma-money/issues/112). Guardrail issue: [#140](https://github.com/Elmorralito/save-ma-money/issues/140).

### Epic close-out DoD (reviewed)

- [x] Feature CRUD UX lives only in the shipped screen modules (no parallel screen scopes under this issue)
- [x] No TypeScript port of `papita_txnsmodel.services.*` (no password hashing, ledger aggregation, or tenant-ownership rules beyond HTTP mapping)
- [x] Auth remains BFF HttpOnly cookies + Supabase IdP; Bearer is for smokes/token clients only
- [x] Spot-check greps under `modules/web` (ignore generated `src/types/api.d.ts` / OpenAPI docstrings): `UsersService`, `bcrypt`/`argon`/`hashPassword`, client-side double-entry / balance aggregation, `class *Service` mirroring model services — **pass** (UI copy may warn _against_ client double-entry)

## Prerequisites

| Tool    | Version                                                               |
| ------- | --------------------------------------------------------------------- |
| Node.js | **22 LTS** (engines: `>=22`; pin via root `.nvmrc` / `.node-version`) |
| pnpm    | **9** (`packageManager` pinned at repo root)                          |

Java is **not** required for the web module.

The SPA proxies `/api` to the Compose API on `:8000`. Start the backend with **`make api-all`** (full stack + health wait) or `make api-up` before `make web-dev`. A **502** from the Vite proxy usually means the API container is down.

From the repo root:

```bash
corepack enable   # optional; or: npm install -g pnpm@9
pnpm install
make api-all      # Postgres + Redis + API (wait for /health/live)
make web-dev      # Vite on :5173
```

## Scripts

| Make (repo root)         | pnpm (repo root)          | Purpose                                                             |
| ------------------------ | ------------------------- | ------------------------------------------------------------------- |
| `make web-dev`           | `pnpm web:dev`            | Vite dev server (default `:5173`)                                   |
| `make web-up`            | —                         | nginx Compose SPA (`WEB_PORT`, default `:3000`) + API deps          |
| `make web-down`          | —                         | Stop the Compose `web` service                                      |
| `make web-lint`          | `pnpm web:lint`           | ESLint + Prettier check                                             |
| `make web-test`          | `pnpm web:test`           | Vitest (jsdom)                                                      |
| `make web-build`         | `pnpm web:build`          | `tsc -b` + production bundle                                        |
| `make generate-types`    | `pnpm web:generate-types` | Regenerate `src/types/api.d.ts` from the committed OpenAPI artifact |
| `make check-types`       | `pnpm web:check-types`    | Fail if `api.d.ts` drifts from the artifact                         |
| `make sync-openapi`      | —                         | Refresh `openapi/openapi.json` from the FastAPI app (offline)       |
| `make check-openapi`     | —                         | Fail if the committed artifact drifts from a fresh offline dump     |
| `make web-openapi`       | —                         | `sync-openapi` + `generate-types` (after API schema changes)        |
| `make web-e2e-seed`      | `pnpm web:seed-e2e`       | Seed Playwright fixtures against a running API                      |
| `make web-test-coverage` | `pnpm web:test:coverage`  | Vitest + v8 coverage thresholds                                     |
| `make web-e2e`           | `pnpm web:test:e2e`       | Playwright critical path + axe (needs `make api-all`)               |
| `make web-lhci`          | `pnpm web:lhci`           | Lighthouse CI lab budgets against `vite preview`                    |
| `make web-audit`         | `pnpm web:audit`          | `pnpm audit --prod` for `@papita/web`                               |

Package-local: `pnpm --filter @papita/web <script>`.

## OpenAPI typegen CI strategy (PPT-065 / #130) — **locked: B**

**Decision:** commit a schema artifact and generate TypeScript from that file. Web CI does **not** boot the API.

| Layer        | Mechanism                                                                                   | Catches                                                                                                                   |
| ------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Artifact     | `modules/web/openapi/openapi.json`                                                          | Checked into git                                                                                                          |
| Types        | `openapi-typescript` → `src/types/api.d.ts`                                                 | `pnpm web:check-types` in [web-ci.yml](../../.github/workflows/web-ci.yml)                                                |
| API↔artifact | Offline `create_app().openapi()` via [`bin/export_openapi.py`](../../bin/export_openapi.py) | [openapi-contract.yml](../../.github/workflows/openapi-contract.yml) on `modules/api/src/**` + model `model/` / `access/` |

The exporter normalizes `info.version` so API package semver bumps alone do not force artifact regen. Optional `make sync-openapi-live` only allows `localhost` / `127.0.0.1`.

**Why not live API in Web CI (option A):** `web-ci` stays Node-only and path-filtered; no Compose/Postgres. Option A would couple every web PR to a heavy API boot with no reusable “API already up” workflow.

**Developer regen (after API OpenAPI-affecting changes):**

```bash
make web-openapi   # sync-openapi && generate-types
# commit: modules/web/openapi/openapi.json + modules/web/src/types/api.d.ts
```

Offline sync is the default (no `make api-up`, no `DOCS_ENABLED` required). Optional live parity:

```bash
make sync-openapi-live   # needs make api-up with DEBUG or DOCS_ENABLED=true
```

If live fetch returns 404, enable docs on the running API or use `make sync-openapi` instead.

Thin schema aliases live in `src/types/domain.ts`.

## Thin HTTP client + TanStack Query (PPT-048 / #114)

Presentation-only client under `src/api/`. **No** `papita_txnsmodel` business logic in TypeScript — typed HTTP + Query wiring only.

| Piece            | Location                                       | Notes                                                                                                       |
| ---------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `apiFetch`       | `src/api/http.ts`                              | `credentials: 'include'`; `AbortSignal`; no `Authorization` header                                          |
| Base URL         | `src/api/config.ts`                            | Default same-origin (`""`) → Vite `/api` proxy; optional `VITE_API_BASE_URL`                                |
| Errors           | `src/api/errors.ts`                            | `PapitaApiError` maps `X-Papita-Error-Code` + discovery headers                                             |
| Contract helpers | `src/api/contract.ts`                          | `bulkMaxTransactions` / `reportWindowMaxDays` from body (prefer) or headers; breaking-changes guard helpers |
| Probes           | `src/api/meta.ts`, `health.ts`                 | Unauthenticated health + `GET /api/v1/meta/client-contract`                                                 |
| Query            | `queryKeys.ts`, `queries.ts`, `queryClient.ts` | `queryOptions()`; `staleTime` 60s; **no 4xx retries**                                                       |
| Breaking guard   | `BreakingChangesGuard` (app root)              | See § Breaking-changes guard below                                                                          |

**Credentials policy:** always send cookies (`credentials: 'include'`) for BFF HttpOnly sessions (PPT-049 / #115). Do **not** store JWTs in `localStorage` / JS-readable storage or attach Bearer tokens from the SPA (PDF Axios interceptor pattern is superseded).

### Breaking-changes guard (PPT-064 / #129)

The SPA expects a stable PPT-044 discovery id (default `ppt-044`) via public env `VITE_PAPITA_BREAKING_CHANGES_ID`. On bootstrap, `BreakingChangesGuard` loads `GET /api/v1/meta/client-contract` (shared `clientContractQueryOptions`) and compares:

1. Body `breaking_changes` (preferred), else
2. Response header `X-Papita-Breaking-Changes` (via shared helpers — **do not** parse that header in feature pages).

| Result       | Behavior                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------- |
| **match**    | Silent                                                                                             |
| **mismatch** | Non-blocking banner for all routes; `console.error` once in DEV, `console.warn` once in production |
| **unknown**  | No banner (probe missing / offline) — avoids false alarms                                          |

Helpers: `evaluateBreakingChangesGuard`, `resolveExpectedBreakingChangesId`, `observedBreakingChangesId` in `src/api/contract.ts`. Feature code must use these instead of ad-hoc header reads.

## BFF cookie auth (PPT-049 / #115)

| Piece         | Location                                                               | Notes                                                                                   |
| ------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| BFF routes    | `POST/GET /api/v1/bff/auth/*`                                          | login, register, session, refresh, logout, OAuth start/callback                         |
| Cookie        | `papita_sid`                                                           | HttpOnly, `SameSite=Lax`, `Path=/api`, `Secure` when not DEBUG                          |
| CSRF          | `X-Papita-CSRF`                                                        | Required on cookie-authenticated mutations; token from login/session JSON (memory only) |
| SPA routes    | `/login`, `/register`, `/check-email`, `/auth/confirm`, feature routes | `RequireAuth` + `AppLayout`; anonymous users redirect to login                          |
| Session query | `queryKeys.auth.session()`                                             | Bootstrap via `GET /bff/auth/session`                                                   |

### Google / GitHub OAuth (operator guide)

Start-to-end setup (Google Cloud / GitHub OAuth App → Supabase Providers → Redirect URLs → local `ALLOWED_ORIGINS` → smoke test):

**[`docs/oauth-supabase-setup.md`](./docs/oauth-supabase-setup.md)**

SPA buttons navigate to `GET /api/v1/bff/auth/oauth/{google|github}` (full page, not `fetch`). Callback sets HttpOnly `papita_sid` and never returns JWTs to JavaScript.

**Threat model (short):**

- **XSS:** HttpOnly session cookie is not readable from JS, so stolen XSS cannot exfiltrate JWTs from storage. Treat XSS as still critical (CSRF token + UI state are reachable). Prefer CSP / dependency hygiene.
- **CSRF:** SameSite=Lax plus required `X-Papita-CSRF` on unsafe methods when the session cookie is present (Bearer token clients are exempt). Login/register/resend-confirmation are CSRF-exempt (anonymous).
- **Phishing / resend abuse:** Confirmation resend is rate-limited with the auth register IP bucket and surfaces SMTP **429** via `formatApiError`; responses soft-succeed for unknown emails (anti-enumeration).
- **Token clients:** `make auth-smoke` and direct `Authorization: Bearer` against `/api/v1/auth/*` still work; they coexist with BFF cookies.

### BFF session durability vs Redis (PPT-059 / #124)

Server-side cookie → token bindings live in API `BffSessionStore` (**not** the JWT denylist `SessionStore`). Redis foundation is PPT-043 ([#83](https://github.com/Elmorralito/save-ma-money/issues/83)); this contract locks when memory is OK vs when Redis is required. Compose/nginx packaging that must keep Redis for durable BFF sessions: § [nginx Compose packaging](#nginx-compose-packaging-ppt-057--122). Full API matrix: [`modules/api/README.md`](../api/README.md) § Workers vs Redis and § Redis.

| Mode                                              | `REDIS_ENABLED`   | Workers | BFF session store                                | Notes                                                                                  |
| ------------------------------------------------- | ----------------- | ------- | ------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Local unit tests / solo host uvicorn              | `false`           | 1       | Process **memory**                               | OK for B0 DX; sessions die on process restart and are **not** shared across workers    |
| Local Compose (`make api-up`)                     | `true` (default)  | 1       | Redis key `papita:{PAPITA_ENV}:bff:session:{id}` | Preferred local path; Compose wires `redis://redis:6379/0`                             |
| Staging / production                              | `true` (required) | 1+      | Redis (same key shape)                           | **Fail-closed** when Redis is required/missing — do not rely on memory for SPA cookies |
| Any env with `--workers N` (N>1) or multi-replica | Must be `true`    | N       | Redis **required**                               | Memory sessions are process-local → lost/sticky logins across workers                  |

**Denylist ≠ BFF map:** logout/revocation uses `papita:{env}:jwt:denylist:{sha256(token)}`. BFF cookie bindings use `papita:{env}:bff:session:{session_id}`. Never reuse denylist helpers for browser sessions (or the reverse).

**Fail policy:** when Redis is required (`REDIS_ENABLED=true`), `BffSessionStore` is **fail closed** (no silent process-memory fallback) → HTTP **503** `BFF session store unavailable`. Operators must run Redis for Compose and staging SPA cookies. Cache/rate-limit remain fail-open; JWT denylist also fails closed — see API Redis docs.

**Local smoke:** `make api-up` then `make web-dev` — open `/login`, sign in (local HS256 or Supabase), confirm `/` shows session + contract probes. Compose defaults to Redis-backed BFF sessions; with `REDIS_ENABLED=false` (single worker only) memory is acceptable for solo local DX.

**Auth smoke note:** `make auth-smoke` exercises **Bearer** `/auth/*` (JWT path), not the HttpOnly `papita_sid` map. It remains valid alongside BFF; it does **not** prove Redis BFF durability. For cookie durability, sign in via the SPA (or call `/api/v1/bff/auth/*`) against a Redis-enabled API.

### Email confirm redirect (PPT-068 / #139)

Same-origin landing: **`/auth/confirm`**. Configure the Supabase project:

| Setting                  | Local Vite                                                             | Compose nginx (`make web-up`)                                 |
| ------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Site URL / Redirect URLs | `http://localhost:5173/auth/confirm`                                   | `http://localhost:<web-port>/auth/confirm` (and staging host) |
| API `ALLOWED_ORIGINS`    | Include `http://localhost:5173` so resend may pass `email_redirect_to` | Include the nginx SPA origin                                  |

The landing page never writes tokens from query/hash into JS storage; it clears the hash and sends the user to `/login` for a BFF cookie session.

**OAuth IdP-verified email (narrow):** Google/GitHub via BFF OAuth (`/api/v1/bff/auth/oauth/*`) treat the IdP email as already verified — do **not** require a second password-signup confirmation gate on the SPA. Password signup remains the confirm-email path above.

**`make auth-smoke` coexistence (confirm-email ON):** use a **already-confirmed** Supabase test user, or run smoke with `AUTH_PROVIDER=local` (confirm-N/A). Do not point auth-smoke at an unconfirmed password user — Bearer login will correctly fail with `email_not_confirmed`. Admin auto-confirm (`AUTH_AUTO_CONFIRM_EMAIL`) is for local DX only, not staging/prod.

## Supabase auth edge-case matrix (PPT-060 / #125)

MVP vs deferred for Supabase Auth behind the BFF. Cookie posture above is unchanged — SPA never stores JWTs. Local DX (Confirm email / `AUTH_AUTO_CONFIRM_EMAIL`) is documented in [`modules/api/README.md`](../api/README.md) (Authentication) and [`environments/local/.env.example`](../../environments/local/.env.example).

| Flow                                    | Decision           | Behavior                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Email + password register/login via BFF | **MVP**            | Primary path (`/login`, `/register` → `/api/v1/bff/auth/*`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Email confirmation required by Supabase | **MVP product UX** | **Local/B0:** Confirm email OFF in the Supabase dashboard **or** Admin auto-confirm when `PAPITA_ENV=local` (`AUTH_AUTO_CONFIRM_EMAIL`, service role). **Staging/prod:** Confirm email **ON**; `AUTH_AUTO_CONFIRM_EMAIL` defaults off outside local. Register returns `email_confirmation_required` and SPA shows `/check-email` (no `papita_sid`). Unconfirmed login maps to allowlisted `"Email not confirmed"` + `X-Papita-Error-Code: email_not_confirmed`. Resend via `POST /api/v1/bff/auth/resend-confirmation` (CSRF-exempt; register rate-limit; optional allowlisted `email_redirect_to`). Confirm landing: SPA `/auth/confirm` (never stores JWTs from the URL). |
| Password reset / forgot password        | **Defer**          | No in-app reset UI or BFF route. Operators recover accounts via the Supabase Auth dashboard (or project recovery email) until a future issue.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Magic link / OTP                        | **Defer**          | Not part of the BFF SPA contract.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| OAuth/SSO buttons                       | **MVP** (BFF)      | Login/Register → BFF OAuth; IdP-verified email (no duplicate confirm gate). Full setup: [`docs/oauth-supabase-setup.md`](./docs/oauth-supabase-setup.md). Bearer `/auth/oauth/*` remains for token clients only.                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Auth rate-limit **429**                 | **MVP**            | App limiter + Supabase SMTP 429 map to allowlisted `detail`; SPA shows them through `formatApiError` (including `Retry-After`) on login/register/resend — not a silent failure.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

### Playwright assumptions

- Default E2E / B0 path uses a **confirmed** (or confirm-N/A) user: CI `AUTH_PROVIDER=local`, or local Supabase with Confirm email OFF / Admin auto-confirm so register → login succeeds without inbox access.
- Unconfirmed-user journeys (`/check-email`, resend, `/auth/confirm`) are covered at **unit** level; do not write Playwright that depends on confirmation email delivery / SMTP.
- Auth **429** is covered at unit level (mapper + login/register pages); e2e rate-limit is optional later.
- **Fixture SSOT:** [E2E fixtures](#e2e-fixtures-ppt-061--126) below. `globalSetup` must call `make web-e2e-seed` (do not invent a second SQL seed).

## E2E fixtures (PPT-061 / #126)

**Locked strategy: A — API seed script** (HTTP against running Compose API). Playwright `globalSetup` only invokes the seed; SQL dumps are out of scope.

| Piece       | Location                                           | Notes                                                                 |
| ----------- | -------------------------------------------------- | --------------------------------------------------------------------- |
| Runner      | [`bin/web_e2e_seed.py`](../../bin/web_e2e_seed.py) | Bearer register/login → accounts → categories → optional baseline txn |
| Wrapper     | [`bin/web_e2e_seed.sh`](../../bin/web_e2e_seed.sh) | Loads `environments/<env>/.env`; supports `RESET=1`                   |
| Artifact    | `modules/web/e2e/.auth/seed.json`                  | **Gitignored** — email/password + IDs for Playwright                  |
| Make / pnpm | `make web-e2e-seed` / `pnpm web:seed-e2e`          | Requires healthy API (`make api-all`)                                 |

**Why not B/C:** Seed logic must not live only inside Playwright (harder to run standalone). SQL fixtures bypass API validation and do not create auth users correctly for local/Supabase.

**Seed contract (owner-scoped, `E2E ` name prefix):**

| Entity       | Stable name                                          | Purpose                                          |
| ------------ | ---------------------------------------------------- | ------------------------------------------------ |
| User         | `E2E_USER_EMAIL` (default `e2e.owner@example.local`) | Fixture tenant                                   |
| Accounts     | `E2E Checking`, `E2E Savings`                        | Expense source + transfer destination            |
| Categories   | `E2E Exp`, `E2E Inc`                                 | Ledger + report UX                               |
| Baseline txn | description `E2E baseline expense`                   | Non-empty spending report before UI creates more |

**Commands:**

```bash
make api-all
make web-e2e-seed              # idempotent: create missing rows only
make web-e2e-seed RESET=1      # soft-delete baseline txns + E2E accounts; recreate; categories reused
pnpm web:seed-e2e              # same as make (honors RESET=1 env)
```

`RESET=1` does **not** soft-delete categories — same-name create after soft-delete can return a phantom 201 against the unique tombstone. Full wipe: new `E2E_USER_EMAIL` or Compose volume reset.

**Env (optional):** `E2E_API_BASE`, `E2E_USER_EMAIL`, `E2E_USER_PASSWORD`, `E2E_USER_USERNAME`, `E2E_SEED_OUT`, `E2E_SKIP_REGISTER=1` (pre-provisioned Supabase user — skip register, login only).

**Auth modes:** Prefer `AUTH_PROVIDER=local` for B0 / CI E2E (no Supabase secrets). Bearer path seeds domain data; Playwright still logs in via BFF cookies in the browser. Token clients (`make auth-smoke`) coexist unchanged.

**CI placement:** Keep PR [`web-ci.yml`](../../.github/workflows/web-ci.yml) Node-only (lint, Vitest+coverage, audit soft-gate, build). Compose seed + Playwright + Lighthouse run in [`web-e2e.yml`](../../.github/workflows/web-e2e.yml) (nightly / `workflow_dispatch` / PRs that touch `e2e/` or seed scripts).

## Quality, a11y, CWV, security (PPT-056 / #121)

Complements auth matrix and E2E fixture sections above.

### Vitest coverage

- Gate: `make web-test-coverage` / `pnpm web:test:coverage` (also PR `web-ci`).
- Thresholds in `vite.config.ts` (pragmatic floor **65%** lines/statements on gated `src/**`; excludes `components/ui/*`, form dialog shells, `main.tsx`, generated types). Stretch toward **~70%** as remaining ledger/auth forms adopt the PPT-055 kit; Playwright covers dialog mutation branches.
- Security unit checks: CSRF memory-only (`src/api/csrf.test.ts`); no JWT persistence after BFF login (`src/api/auth.security.test.ts`).

### Playwright + axe

```bash
make api-all
# Local tip: set API_RATE_LIMIT_ENABLED=false (and auth rate limits off) in
# environments/local/.env if burst e2e traffic hits 429 — CI already disables them.
make web-e2e    # globalSetup → make web-e2e-seed; critical path + axe
```

| Spec                         | What                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------- |
| `e2e/critical-path.spec.ts`  | BFF login (seed) → create account → expense → transfer → spending report; no JWT in WebStorage |
| `e2e/a11y.spec.ts`           | axe (`wcag2a`/`wcag2aa`/`wcag21a`/`wcag21aa`) on login/register + MVP authed routes            |
| `e2e/register-login.spec.ts` | Optional SPA register; enable with `E2E_LIVE_REGISTER=1`                                       |

Config: `playwright.config.ts` (Vite `webServer` on `:5173`, Chromium).

### WCAG 2.1 AA intent (MVP)

Documented as **met for MVP flows** when:

- axe reports **no critical/serious** violations on `/login`, `/register`, `/dashboard`, `/accounts`, `/categories`, `/transactions`, `/movements`, `/reports`, `/payment-dues`
- Keyboard: native controls + Radix dialogs; global `:focus-visible` ring in `src/index.css`
- Labels: form fields use `<Label htmlFor>` / dialog field ids; eslint `jsx-a11y` on PRs
- Contrast: design tokens in `src/index.css` (light default); dark aliases available

Deferred polish (not blockers): full screen-reader scripted journeys, mobile native a11y.

### RUM / Sentry (deferred)

**Field RUM, Sentry, and production error-reporting SDKs are deferred post-MVP.** Do not add browser observability vendors for the PPT-046 MVP. Lab-only Lighthouse / Core Web Vitals budgets live in this section (`make web-lhci` / `web-e2e.yml`) — not a substitute for field RUM.

### Lighthouse / Core Web Vitals (lab)

`make web-lhci` after build — config `lighthouserc.cjs`:

| Budget                        | Gate  | Notes                                                                 |
| ----------------------------- | ----- | --------------------------------------------------------------------- |
| Accessibility category ≥ 0.95 | error | Aligns with axe intent                                                |
| Performance category ≥ 0.9    | warn  | Lab; may need waiver on cold CI runners                               |
| LCP ≤ 2.5s                    | warn  | Lab                                                                   |
| CLS ≤ 0.1                     | error | Lab                                                                   |
| TBT ≤ 200ms                   | warn  | **INP proxy** — Lighthouse CI asserts TBT; true INP is field-oriented |

**Waiver posture:** performance / LCP / TBT are `warn` so flaky lab noise does not block the nightly gate; a11y score + CLS remain hard. Record failing lab runs in the PR/issue with rationale if promoting to required checks later.

### Security checklist (BFF / CSP / deps)

| Check                     | Status / owner                                                                                                            |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| No JWT in WebStorage      | Enforced by design + unit/e2e asserts                                                                                     |
| Cookie flags              | API BFF: `papita_sid` HttpOnly, `SameSite=Lax`, `Path=/api`, `Secure` when not DEBUG (see BFF section)                    |
| CSRF                      | `X-Papita-CSRF` from memory (`src/api/csrf.ts`)                                                                           |
| `pnpm audit` / Dependabot | `make web-audit`; Dependabot ecosystem `npm` dir `modules/web` (`npm-web` group)                                          |
| gitleaks / `VITE_*`       | Never put secrets in `VITE_*`; repo gitleaks workflow scans PRs                                                           |
| CSP headers               | nginx SPA locations only (see [CSP (nginx)](#csp-nginx)); no Vite meta CSP                                                |
| nginx Compose packaging   | `docker/web/` + `make web-up` (same-origin `/api`) — see [nginx Compose packaging](#nginx-compose-packaging-ppt-057--122) |

PR template section **Web security checklist** must be signed off on web/auth PRs.

## Vite `/api` proxy

`vite.config.ts` proxies `/api` → `http://localhost:8000` so local browser calls stay same-origin. Start the API with `make api-up` when you need a live backend; **lint / test / build do not require the API**.

## nginx Compose packaging (PPT-057 / #122)

Primary deploy path is **nginx in Compose** (not Vercel/Netlify/S3). Multi-stage image: pnpm build → `nginxinc/nginx-unprivileged` (non-root, port 8080) with SPA fallback and `/api` reverse-proxy to the `api` service.

**Registry (PPT-067):** GHCR `save-ma-money-web` publishes from `main` via [`publish-web-image.yml`](../../.github/workflows/publish-web-image.yml) (PR `pr-*`/`dev-*` unless `skip-web-image-dev`). Local: `make web-image-build` + `./.github/scripts/web_image_smoke.sh papita-web:local`. Naming SSOT: [`docker/README.md`](../../docker/README.md).

**Git tags (PPT-066 / [#131](https://github.com/Elmorralito/save-ma-money/issues/131)):** when this package cuts a source release, use `js-web-v{semver}` (semver from `package.json`). That is a **Git tag / GitHub Release** convention only — GHCR image publish stays on `main` path triggers (see [`docker/README.md`](../../docker/README.md)). Convention SSOT: [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066).

| Piece      | Location                                              | Notes                                                                                                          |
| ---------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Dockerfile | `docker/web/Dockerfile`                               | Bake public `VITE_*` as build-args; leave `VITE_API_BASE_URL` empty for same-origin `/api`; non-root (DS-0002) |
| nginx      | `docker/web/nginx.conf` + `spa-security-headers.conf` | Listen `8080`; SPA shell; `/api` → `api:8000`; CSP + baseline headers on static locations only (PPT-063)       |
| Compose    | `docker/docker-compose.yml` `web`                     | Publishes `WEB_PORT`→`8080` (default host `3000`); `depends_on` healthy `api` + `redis` (PPT-059)              |
| Make       | `make web-up` / `web-down`                            | Builds/starts `web` + deps; smokes `/` + health + CSP headers. `make stack-up` includes `web`                  |

**Local Vite vs Compose nginx**

| Mode              | Command                         | Origin                          | When to use                                  |
| ----------------- | ------------------------------- | ------------------------------- | -------------------------------------------- |
| Day-to-day DX     | `make api-all` + `make web-dev` | Vite `:5173` (proxy → `:8000`)  | Hot reload, feature work                     |
| Packaging / smoke | `make web-up`                   | nginx `WEB_PORT` (default 3000) | Validate prod-shaped same-origin BFF cookies |

Cookie notes (aligned with [BFF section](#bff-cookie-auth-ppt-049--115)):

- Browser talks only to nginx; `/api` is same-origin → no brittle cross-site cookie CORS.
- `papita_sid` remains HttpOnly, `SameSite=Lax`, `Path=/api`; nginx must not rewrite cookie Path.
- Staging/prod: set `ALLOWED_ORIGINS` to the **web** origin(s); never `*` with credentials. Redis required in the stack (no memory BFF fallback).

### CSP (nginx)

Production-shaped headers are set by nginx on **static SPA locations only** (`/`, `/index.html`, `/assets/`). The `/api` proxy does **not** attach SPA CSP — API responses keep [`SecurityHeadersMiddleware`](../api/src/papita_txnsapi/middleware/security_headers.py) (nosniff / no-referrer / DENY; no API CSP so Swagger can work when docs are on).

| Header                    | Value (summary)                                                                                                                                                                                                                        |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Content-Security-Policy` | `default-src 'self'`; `script-src 'self'`; `style-src 'self' 'unsafe-inline'`; `img-src 'self' data:`; `font-src 'self'`; `connect-src 'self'`; `object-src 'none'`; `base-uri 'self'`; `form-action 'self'`; `frame-ancestors 'none'` |
| `X-Content-Type-Options`  | `nosniff`                                                                                                                                                                                                                              |
| `Referrer-Policy`         | `no-referrer`                                                                                                                                                                                                                          |
| `X-Frame-Options`         | `DENY`                                                                                                                                                                                                                                 |

**Residual risk:** `style-src 'unsafe-inline'` is required today for Radix/shadcn inline positioning styles. Scripts stay strict (`'self'` only — no `'unsafe-inline'` / `'unsafe-eval'`). A nonce/`'unsafe-hashes'` pipeline is deferred post-MVP.

**`connect-src 'self'`:** Compose bake must keep `VITE_API_BASE_URL` empty so the browser calls same-origin `/api`. Baking an absolute cross-origin API URL would be blocked by CSP (and fights the BFF cookie same-origin design).

**DX vs packaging:** Vite (`make web-dev` / Playwright `:5173`) does **not** emit these headers. Assert CSP via `make web-up` or Web CI `web-docker` smoke — not the Vite critical-path e2e.

```bash
make web-up
# open http://localhost:3000/ → login via BFF; cookies scoped to Path=/api on the web origin
# curl -sI http://localhost:3000/ | grep -i content-security-policy
```

## CORS / `ALLOWED_ORIGINS`

- API default / documented local CORS targets include `http://localhost:3000` (and `127.0.0.1:3000`) for the nginx SPA and `http://localhost:5173` for Vite.
- With the Vite proxy, the browser talks to Vite (`:5173`) and `/api` is same-origin — CORS is not involved for those calls.
- With `make web-up`, the browser talks to nginx (`:3000`) and `/api` is same-origin through the proxy — CORS is not involved for those calls either.
- If you call the API **cross-origin** from `:5173` (no proxy / absolute `VITE_API_BASE_URL` to `:8000`), add `http://localhost:5173` to `ALLOWED_ORIGINS` in `environments/local/.env`.

## `VITE_*` env rules

- Only **public** values may use the `VITE_` prefix — Vite embeds them in the client bundle.
- Copy `.env.example` → `.env.local` for local overrides (gitignored via `*.local`).
- Never put secrets, service-role keys, or JWT signing material in `VITE_*` variables.

## Design system + app shell (PPT-051 / #116)

| Piece      | Location                  | Notes                                                                                                                                                                |
| ---------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tokens     | `src/index.css`           | CSS variables (`--background`, `--primary`, …) + `.dark` aliases; Tailwind v4 via `@tailwindcss/vite`                                                                |
| Primitives | `src/components/ui/*`     | shadcn/ui (new-york): Button, Input, Label, Dialog, Dropdown, Table, Separator, Sonner                                                                               |
| Layouts    | `src/components/layout/*` | `PublicLayout` (auth), `AppLayout` (nav shell); hideable sidebar (toggle + localStorage)                                                                             |
| Routes     | `src/App.tsx`             | Lazy routes: auth (login/register), accounts (+ detail), categories (PPT-052), transactions/movements (PPT-053), dashboard/reports (PPT-054), payment dues (PPT-074) |

Add a component:

```bash
cd modules/web
pnpm dlx shadcn@latest add <component>   # uses components.json aliases
```

Feature pages should consume tokens / `ui/*` primitives — avoid one-off hex colors.

## Quality gates

- TypeScript: `strict` + `noUncheckedIndexedAccess`; path alias `@/*` → `src/*`.
- ESLint (flat) + Prettier + `eslint-plugin-react-hooks` + `eslint-plugin-jsx-a11y` + `@tanstack/eslint-plugin-query`.
- OpenAPI types must stay in sync (`make check-types`); API PRs must refresh the artifact (`make check-openapi`).
- Vitest coverage thresholds (PPT-056) on PR via `web-ci`; Playwright/axe/Lighthouse via `web-e2e` (see [Quality section](#quality-a11y-cwv-security-ppt-056--121)).
- **Local pre-commit (web):** when staging `modules/web/**`, [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) runs `web-eslint`, `web-prettier`, `web-tsc`, and `web-vitest-related` via [`.github/scripts/pre_commit_web.sh`](../../.github/scripts/pre_commit_web.sh) (same tools as husky+lint-staged, without husky). Requires `pnpm install`. Skipped in Python quality-control CI; [`.github/workflows/web-ci.yml`](../../.github/workflows/web-ci.yml) remains the Node merge gate.
- Not using husky/commitlint here — commit titles follow repo PPT notation (`feat/PPT-NNN: [web] …`); Stylelint omitted (Tailwind v4 + token CSS, no separate SCSS pipeline).

## Forms & UX standards (PPT-055 / #120)

Shared validation and mutation error UX live under `src/forms/`. Feature screens should use this kit instead of ad-hoc `useState` + throw validation.

| Piece           | Location                                          | Notes                                                                           |
| --------------- | ------------------------------------------------- | ------------------------------------------------------------------------------- |
| Deps            | `zod`, `react-hook-form`, `@hookform/resolvers`   | Owned by PPT-055                                                                |
| Schemas         | `src/forms/schemas/*`                             | UX shape checks aligned to OpenAPI write models — **not** a second domain layer |
| Field chrome    | `src/forms/FormField.tsx`                         | Label + control + inline `role="alert"` error                                   |
| Server → fields | `src/forms/mapServerErrors.ts`                    | FastAPI 422 `loc` + optional `fieldMap` → RHF paths                             |
| Mutation policy | `src/forms/applyMutationError.ts`                 | See error table below                                                           |
| Money / dates   | `src/lib/formatMoney.ts`, `src/lib/formatDate.ts` | `Intl` presentation helpers only                                                |
| Query chrome    | `src/components/QueryState.tsx`                   | Pending / empty / error for list-detail fetches                                 |

**Mutation error policy**

| Class                        | UX                                                                                |
| ---------------------------- | --------------------------------------------------------------------------------- |
| Zod client validation        | Inline field errors only                                                          |
| HTTP 422 with mappable `loc` | Inline `setError` (field / root); **no** toast                                    |
| 429 / network / 502–504      | Toast via `formatApiError` (+ `Retry-After` when present) **and** root form error |
| Other 4xx/5xx                | Toast + root form error                                                           |
| Global category 404          | Inline + toast (read-only seed signal; unchanged)                                 |

**Pending:** disable submit while `mutation.isPending` or `formState.isSubmitting`; button label `Saving…`.

Reference migrations: `AccountFormDialog` + `CategoryFormDialog`. Ledger/auth forms may adopt the same kit later.

## Feature screens (PPT-052)

Accounts and categories call `/api/v1/accounts` and `/api/v1/categories` via `src/api/accounts.ts` / `categories.ts` + `queryOptions` (`credentials: 'include'` via `apiFetch`). Forms use Zod + RHF (`src/forms/`). Global seed category writes surface as HTTP 404 `Category not found` and are mapped to a read-only UX.

| Detail          | Behavior                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------- |
| List window     | First page only (`limit=100`); footer notes when `total > 100`                                 |
| Money display   | `src/lib/formatMoney.ts` (presentation only)                                                   |
| Update payloads | Omit empty optional fields so edits do not wipe server values                                  |
| Errors          | `formatApiError` — 502/503/504 → start API; 429 → server detail (+ `Retry-After` when present) |
| Auth UX         | Register confirm-password + show/hide; login banner after successful register                  |

## Ledger screens (PPT-053 / #118)

Transactions and movements call `/api/v1/transactions` and `/api/v1/movements` via `src/api/transactions.ts` / `movements.ts` + `queryOptions`. Presentation only — no TypeScript ports of ledger services. Forms are still controlled `useState` (optional follow-on onto the PPT-055 kit).

| Detail           | Behavior                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| Default txn list | Omits `transaction_type` so the API excludes transfers                                            |
| Idempotency      | `Idempotency-Key` always sent on create/bulk (`src/api/idempotency.ts`); replay needs Redis       |
| Bulk             | Cap from `bulkMaxTransactions(client-contract)` (fallback 100); surfaces `bulk_too_large`         |
| Movements        | Create immediate (`scheduled: false`) or pending; Execute / Cancel only when `status === pending` |
| Invalidation     | After writes: txn/movement lists + account lists/details (API balances)                           |
| Split            | API `POST .../split` returns 501 — **not** exposed in the SPA (deferred to v4)                    |
| 429              | Mutations toast `formatApiError` including optional Retry-After seconds                           |

## Payment dues + Due soon (PPT-074 / #167)

In-app payment due-date reminders (epic PPT-070 / [#163](https://github.com/Elmorralito/save-ma-money/issues/163)). Presentation only over `/api/v1/transaction-templates` — no TypeScript ports of dues/window math.

| Piece            | Location                                                              | Notes                                                            |
| ---------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| List / CRUD page | `src/pages/PaymentDuesPage.tsx` · route `/payment-dues`               | Create/edit dues; nav label “Payment dues”                       |
| Form state       | `src/components/paymentDues/*`                                        | Dialog + form state helpers                                      |
| Due soon         | `src/pages/DashboardPage.tsx`                                         | Dashboard panel titled **Due soon** (`upcomingDuesQueryOptions`) |
| API client       | `src/api/transactionTemplates.ts` · `src/api/queries.ts`              | `credentials: 'include'` via `apiFetch`; BFF cookies only        |
| Types            | Generated from committed OpenAPI (`make web-openapi` / `check-types`) | Paths include upcoming-dues / mark-paid / clear-paid             |

Epic index: [`docs/issues/README.md` Part VIII](../../docs/issues/README.md#part-viii--ppt-070-payment-due-date-reminders-163).

## Out of scope here

Durable deferrals (not closed delivery tickets):

- Transaction split v4 UI; budgets / budget-performance surfaces
- Email / push / calendar feeds for payment dues (PPT-070 deferred)
- Field RUM / Sentry / production error-reporting SDKs (lab Lighthouse/CWV only — see Quality section)
- Mobile native apps; public marketing SSR
- TypeScript ports of model services — see [Domain boundary](#domain-boundary-ppt-069--140)
