---
id: 20260803-05
type: task
status: open
severity: med
area: modules/web
created: 2026-08-03
---

**What:** PPT-061 [#126](https://github.com/Elmorralito/save-ma-money/issues/126) deterministic E2E seed fixtures for Playwright critical path (strategy A — API HTTP script).

**Why:** Blocks reliable [#121](https://github.com/Elmorralito/save-ma-money/issues/121) Playwright gate. Fixture SSOT so `globalSetup` does not invent a second SQL seed.

**Progress**

- `bin/web_e2e_seed.py` / `bin/web_e2e_seed.sh`, `make web-e2e-seed`, `pnpm web:seed-e2e`
- Artifact `modules/web/e2e/.auth/seed.json` (gitignored)
- Docs in `modules/web/README.md` + `modules/web/e2e/README.md`

**Still open / handoff**

- Playwright `globalSetup` + Compose E2E CI owned by #121
- Close #126 after PR merge; cite fixture SSOT from #121
