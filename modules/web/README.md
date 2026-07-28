# `@papita/web`

React + TypeScript SPA scaffold for the Papita finance client ([PPT-047](https://github.com/Elmorralito/save-ma-money/issues/113) · epic [PPT-046](https://github.com/Elmorralito/save-ma-money/issues/112)).

This package is presentation-only. Domain rules stay in `papita_txnsmodel` behind `papita_txnsapi` — do not reimplement business logic here.

## Prerequisites

| Tool    | Version                                                               |
| ------- | --------------------------------------------------------------------- |
| Node.js | **22 LTS** (engines: `>=22`; pin via root `.nvmrc` / `.node-version`) |
| pnpm    | **9** (`packageManager` pinned at repo root)                          |

Java is **not** required for the web module.

From the repo root:

```bash
corepack enable   # optional; or: npm install -g pnpm@9
pnpm install
```

## Scripts

| Make (repo root) | pnpm (repo root) | Purpose                           |
| ---------------- | ---------------- | --------------------------------- |
| `make web-dev`   | `pnpm web:dev`   | Vite dev server (default `:5173`) |
| `make web-lint`  | `pnpm web:lint`  | ESLint + Prettier check           |
| `make web-test`  | `pnpm web:test`  | Vitest (jsdom)                    |
| `make web-build` | `pnpm web:build` | `tsc -b` + production bundle      |

Package-local: `pnpm --filter @papita/web <script>`.

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

## Quality gates

- TypeScript: `strict` + `noUncheckedIndexedAccess`; path alias `@/*` → `src/*`.
- ESLint 9 (flat) + Prettier + `eslint-plugin-react-hooks` + `@tanstack/eslint-plugin-query`.
- Python pre-commit remains for Python; web quality is enforced by [`.github/workflows/web-ci.yml`](../../.github/workflows/web-ci.yml).

## Out of scope here

Feature screens, BFF cookie auth, OpenAPI client, design system / shadcn shell, nginx image — see epic children under [#112](https://github.com/Elmorralito/save-ma-money/issues/112).
