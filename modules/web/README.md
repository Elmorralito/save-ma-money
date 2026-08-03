# `@papita/web`

React + TypeScript SPA scaffold for the Papita finance client ([PPT-047](https://github.com/Elmorralito/save-ma-money/issues/113) · epic [PPT-046](https://github.com/Elmorralito/save-ma-money/issues/112)).

This package is presentation-only. Domain rules stay in `papita_txnsmodel` behind `papita_txnsapi` — do not reimplement business logic here.

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

| Make (repo root)      | pnpm (repo root)          | Purpose                                                             |
| --------------------- | ------------------------- | ------------------------------------------------------------------- |
| `make web-dev`        | `pnpm web:dev`            | Vite dev server (default `:5173`)                                   |
| `make web-lint`       | `pnpm web:lint`           | ESLint + Prettier check                                             |
| `make web-test`       | `pnpm web:test`           | Vitest (jsdom)                                                      |
| `make web-build`      | `pnpm web:build`          | `tsc -b` + production bundle                                        |
| `make generate-types` | `pnpm web:generate-types` | Regenerate `src/types/api.d.ts` from the committed OpenAPI artifact |
| `make check-types`    | `pnpm web:check-types`    | Fail if `api.d.ts` drifts from the artifact                         |
| `make sync-openapi`   | —                         | Refresh `openapi/openapi.json` from the FastAPI app (offline)       |
| `make check-openapi`  | —                         | Fail if the committed artifact drifts from a fresh offline dump     |
| `make web-openapi`    | —                         | `sync-openapi` + `generate-types` (after API schema changes)        |

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

| Piece            | Location                                       | Notes                                                                        |
| ---------------- | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| `apiFetch`       | `src/api/http.ts`                              | `credentials: 'include'`; `AbortSignal`; no `Authorization` header           |
| Base URL         | `src/api/config.ts`                            | Default same-origin (`""`) → Vite `/api` proxy; optional `VITE_API_BASE_URL` |
| Errors           | `src/api/errors.ts`                            | `PapitaApiError` maps `X-Papita-Error-Code` + discovery headers              |
| Contract helpers | `src/api/contract.ts`                          | `bulkMaxTransactions` / `reportWindowMaxDays` from body (prefer) or headers  |
| Probes           | `src/api/meta.ts`, `health.ts`                 | Unauthenticated health + `GET /api/v1/meta/client-contract`                  |
| Query            | `queryKeys.ts`, `queries.ts`, `queryClient.ts` | `queryOptions()`; `staleTime` 60s; **no 4xx retries**                        |

**Credentials policy:** always send cookies (`credentials: 'include'`) for BFF HttpOnly sessions (PPT-049 / #115). Do **not** store JWTs in `localStorage` / JS-readable storage or attach Bearer tokens from the SPA (PDF Axios interceptor pattern is superseded).

## BFF cookie auth (PPT-049 / #115)

| Piece         | Location                                                                | Notes                                                                                   |
| ------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| BFF routes    | `POST/GET /api/v1/bff/auth/*`                                           | login, register, session, refresh, logout                                               |
| Cookie        | `papita_sid`                                                            | HttpOnly, `SameSite=Lax`, `Path=/api`, `Secure` when not DEBUG                          |
| CSRF          | `X-Papita-CSRF`                                                         | Required on cookie-authenticated mutations; token from login/session JSON (memory only) |
| SPA routes    | `/login`, `/register`, `/dashboard`, accounts/categories/txns/movements | `RequireAuth` + `AppLayout`; anonymous users redirect to login                          |
| Session query | `queryKeys.auth.session()`                                              | Bootstrap via `GET /bff/auth/session`                                                   |

**Threat model (short):**

- **XSS:** HttpOnly session cookie is not readable from JS, so stolen XSS cannot exfiltrate JWTs from storage. Treat XSS as still critical (CSRF token + UI state are reachable). Prefer CSP / dependency hygiene.
- **CSRF:** SameSite=Lax plus required `X-Papita-CSRF` on unsafe methods when the session cookie is present (Bearer token clients are exempt).
- **Token clients:** `make auth-smoke` and direct `Authorization: Bearer` against `/api/v1/auth/*` still work; they coexist with BFF cookies.

**Local smoke:** `make api-up` then `make web-dev` — open `/login`, sign in (local HS256 or Supabase), confirm `/` shows session + contract probes. Memory BFF sessions are process-local (document multi-worker limitation; Redis when `REDIS_ENABLED=true`).

## Supabase auth edge-case matrix (PPT-060 / #125)

MVP vs deferred for Supabase Auth behind the BFF. Cookie posture above is unchanged — SPA never stores JWTs. Local DX (Confirm email / `AUTH_AUTO_CONFIRM_EMAIL`) is documented in [`modules/api/README.md`](../api/README.md) (Authentication) and [`environments/local/.env.example`](../../environments/local/.env.example).

| Flow                                    | Decision                             | Behavior                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Email + password register/login via BFF | **MVP**                              | Primary path (`/login`, `/register` → `/api/v1/bff/auth/*`)                                                                                                                                                                                                                                                                                                                                                                                           |
| Email confirmation required by Supabase | **Document now; product UX in #139** | **Local/B0:** Confirm email OFF in the Supabase dashboard **or** Admin auto-confirm when `PAPITA_ENV=local` (`AUTH_AUTO_CONFIRM_EMAIL`, service role). **Staging/prod:** expect Confirm email **ON**; `AUTH_AUTO_CONFIRM_EMAIL` defaults off outside local. Check-email / resend / confirm callback are owned by [PPT-068 #139](https://github.com/Elmorralito/save-ma-money/issues/139). SPA maps `"Email not confirmed"` via `formatApiError` only. |
| Password reset / forgot password        | **Defer**                            | No in-app reset UI or BFF route. Operators recover accounts via the Supabase Auth dashboard (or project recovery email) until a future issue.                                                                                                                                                                                                                                                                                                         |
| Magic link / OTP                        | **Defer**                            | Not part of the BFF SPA contract.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| OAuth/SSO buttons                       | **Defer**                            | Bearer `/auth/oauth/*` may exist on the API; SPA buttons are epic OOS.                                                                                                                                                                                                                                                                                                                                                                                |
| Auth rate-limit **429**                 | **MVP**                              | App limiter + Supabase SMTP 429 map to allowlisted `detail`; SPA shows them through `formatApiError` (including `Retry-After`) on login/register — not a silent failure.                                                                                                                                                                                                                                                                              |

### Playwright assumptions (#121)

- Default E2E / B0 path uses a **confirmed** (or confirm-N/A) user: CI `AUTH_PROVIDER=local`, or local Supabase with Confirm email OFF / Admin auto-confirm so register → login succeeds without inbox access.
- Unconfirmed-user journeys (pending screen, resend, SMTP) are **out of Playwright MVP until #139** — do not write e2e that depends on confirmation email delivery.
- Auth **429** is covered at unit level (mapper + login/register pages); e2e rate-limit is optional later.

## Vite `/api` proxy

`vite.config.ts` proxies `/api` → `http://localhost:8000` so local browser calls stay same-origin. Start the API with `make api-up` when you need a live backend; **lint / test / build do not require the API**.

## CORS / `ALLOWED_ORIGINS`

- API default / documented local CORS targets include `http://localhost:3000` (and `127.0.0.1:3000`).
- With the Vite proxy, the browser talks to Vite (`:5173`) and `/api` is same-origin — CORS is not involved for those calls.
- If you call the API **cross-origin** from `:5173` (no proxy / absolute `VITE_API_BASE_URL` to `:8000`), add `http://localhost:5173` to `ALLOWED_ORIGINS` in `environments/local/.env`.

## `VITE_*` env rules

- Only **public** values may use the `VITE_` prefix — Vite embeds them in the client bundle.
- Copy `.env.example` → `.env.local` for local overrides (gitignored via `*.local`).
- Never put secrets, service-role keys, or JWT signing material in `VITE_*` variables.

## Design system + app shell (PPT-051 / #116)

| Piece      | Location                  | Notes                                                                                                                                        |
| ---------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Tokens     | `src/index.css`           | CSS variables (`--background`, `--primary`, …) + `.dark` aliases; Tailwind v4 via `@tailwindcss/vite`                                        |
| Primitives | `src/components/ui/*`     | shadcn/ui (new-york): Button, Input, Label, Dialog, Dropdown, Table, Separator, Sonner                                                       |
| Layouts    | `src/components/layout/*` | `PublicLayout` (auth), `AppLayout` (nav shell); mobile drawer + desktop sidebar                                                              |
| Routes     | `src/App.tsx`             | Lazy routes: auth (login/register), accounts (+ detail), categories (PPT-052), transactions/movements (PPT-053), dashboard/reports (PPT-054) |

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
- **Local pre-commit (web):** when staging `modules/web/**`, [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) runs `web-eslint`, `web-prettier`, `web-tsc`, and `web-vitest-related` via [`.github/scripts/pre_commit_web.sh`](../../.github/scripts/pre_commit_web.sh) (same tools as husky+lint-staged, without husky). Requires `pnpm install`. Skipped in Python quality-control CI; [`.github/workflows/web-ci.yml`](../../.github/workflows/web-ci.yml) remains the merge gate.
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

Accounts and categories call `/api/v1/accounts` and `/api/v1/categories` via `src/api/accounts.ts` / `categories.ts` + `queryOptions` (`credentials: 'include'` via `apiFetch`). Forms use Zod + RHF (`src/forms/`, PPT-055 / [#120](https://github.com/Elmorralito/save-ma-money/issues/120)). Global seed category writes surface as HTTP 404 `Category not found` and are mapped to a read-only UX.

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

## Out of scope here

Dashboard/reports UI (PPT-054), transaction split v4 UI, migrating remaining ledger/auth forms onto PPT-055, nginx image, Redis session durability polish (#124) — see epic children under [#112](https://github.com/Elmorralito/save-ma-money/issues/112). Auth edge-case matrix is above (PPT-060 / #125); email-confirm product UX is [#139](https://github.com/Elmorralito/save-ma-money/issues/139).
