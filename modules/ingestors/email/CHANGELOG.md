# Changelog — papita-ingestor-email

Release notes for the **`papita-ingestor-email`** package.

This file is **not** the monorepo issue tracker changelog. Root
[`CHANGELOG.md`](../../../CHANGELOG.md) is owned by
[`.github/workflows/auto-updates.yml`](../../../.github/workflows/auto-updates.yml).

## 0.0.1 (unreleased)

### Added

- Package scaffold for PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)
  (`src/papita_ingestor_email`, smoke tests, path dependency on
  `papita-ingestor-core`).
- Bank email parsers for PPT-081 / [#175](https://github.com/Elmorralito/save-ma-money/issues/175):
  `BancolombiaParser`, synthetic `NequiParser`, hybrid `FallbackEmailParser`,
  MIME helpers, sanitized `.eml` fixtures, and `ensure_parsers_registered()`.
- Prefect email flow + packaging for PPT-082 / [#176](https://github.com/Elmorralito/save-ma-money/issues/176):
  `flows/email_flow.py`, `EmailFlowDeps` wiring, `EmailFlowSettings`,
  owner from `PAPITA_INGESTOR_OWNER_ID`, `runtime.py` (env file, DB establish,
  Gmail/owner preflight, H1 warning), Compose profile `ingestor` + runner `/health`.
