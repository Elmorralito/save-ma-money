# E2E (PPT-056 / #121 + fixtures PPT-061 / #126)

## Fixtures

Fixture SSOT is the **API HTTP seed** (option A) — see
[`../README.md`](../README.md#e2e-fixtures-ppt-061--126).

```bash
make api-all
make web-e2e-seed              # or: pnpm web:seed-e2e
make web-e2e-seed RESET=1      # baseline txns + E2E accounts; categories reused
```

Artifact (gitignored): `.auth/seed.json`.

`playwright.config.ts` → `e2e/global-setup.ts` invokes **`make web-e2e-seed` only**
(do not invent a second SQL seed).

## Auth assumptions (PPT-060 / #125 + PPT-068 / #139)

- Default path: **confirmed** (or confirm-N/A) seed user → BFF cookie login.
- Unconfirmed / resend / SMTP delivery stay **out of Playwright**; unit coverage lives under PPT-068 (`/check-email`, resend, `/auth/confirm`).
- Optional SPA register: `E2E_LIVE_REGISTER=1 pnpm web:test:e2e` (requires confirm-N/A IdP).
- `make auth-smoke` (Bearer) coexists: confirmed Supabase user or `AUTH_PROVIDER=local`.

## Commands

```bash
make api-all
make web-e2e                   # Playwright critical path + axe
# or: pnpm web:test:e2e
```

CI: [`.github/workflows/web-e2e.yml`](../../../.github/workflows/web-e2e.yml)
(nightly / `workflow_dispatch` / PRs that touch e2e or seed scripts). PR
[`web-ci.yml`](../../../.github/workflows/web-ci.yml) stays Node-only.
