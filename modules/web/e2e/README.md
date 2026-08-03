# E2E fixtures (PPT-061 / #126)

Fixture SSOT for Playwright critical-path data. Seed strategy is **API HTTP script**
(option A) — see [`../README.md`](../README.md#e2e-fixtures-ppt-061--126).

```bash
make api-all
make web-e2e-seed              # or: pnpm web:seed-e2e
make web-e2e-seed RESET=1      # baseline txns + E2E accounts; categories reused
```

Artifact (gitignored): `.auth/seed.json`. Playwright wiring lives in [#121](https://github.com/Elmorralito/save-ma-money/issues/121) (`globalSetup` should invoke this command only — do not invent a second SQL seed).
