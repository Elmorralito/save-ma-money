---
name: web e2e ppt056
description: Playwright globalSetup must call make web-e2e-seed only; keep web-ci Node-only.
type: learning
---

When adding or changing Playwright / web E2E (PPT-056 / #121):

- Fixture SSOT is PPT-061 (`make web-e2e-seed`). `globalSetup` invokes that only — no second SQL seed.
- Auth assumptions from PPT-060: confirmed (or confirm-N/A) seed user; optional `E2E_LIVE_REGISTER=1`.
- Keep PR `web-ci.yml` Node-only (Vitest+coverage). Compose + Playwright + Lighthouse live in `web-e2e.yml`.
- SPA `toAccountCreate` must **omit** empty `initial_value` (JSON null → SQL NULL → list path can surface NaN via DataFrame→DTO).
- Local e2e tip: disable API/auth rate limits if 429 flakes; CI already sets them false.
