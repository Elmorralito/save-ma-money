# Memory Index — save-ma-money

Pure hot index: live pointers + the generated rules-by-trigger table. Keep ≤80 lines. Structure and routing live in `.strata/MANIFEST.md`, not here.

## Live pointers

- [Project state](project_state.md) — PPT-081 / #175 in progress (bank email parsers); PPT-080 closed.
- [Active issues](../issues/ACTIVE.md) — prefer project_state for in-flight PR (PPT-081).
- [Open backlog](../issues/OPEN.md) — PPT-076 epic children after #175.
- Closed work — GitHub issues + `git log` (no `.strata/issues/archive/`).

## Rules by trigger

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| When you are about to…                                       | Read                                                                         |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Change auth, register, login, users passwords, or JWT issue  | [supabase-auth-ownership.md](learnings/supabase-auth-ownership.md)           |
| Change local register/login or `AUTH_AUTO_CONFIRM_EMAIL`     | [local-supabase-email-confirm.md](learnings/local-supabase-email-confirm.md) |
| Commit under `modules/api/src`                               | [api-pre-commit-lint.md](learnings/api-pre-commit-lint.md)                   |
| Commit when `modules/` or `bin/` changed                     | [strata-strict-pairing.md](learnings/strata-strict-pairing.md)               |
| Parse DataFrames → DTOs with optional int/date columns       | [pandas-optional-int-nan.md](learnings/pandas-optional-int-nan.md)           |
| Wire `/reports/*` or ReportService                           | [report-tenant-scoping.md](learnings/report-tenant-scoping.md)               |
| Add transactions/movements/bulk UI in `modules/web`          | [web-ledger-ui-no-domain.md](learnings/web-ledger-ui-no-domain.md)           |
| Add or refactor SPA forms / Zod / RHF / mutation errors      | [web-forms-ux-kit.md](learnings/web-forms-ux-kit.md)                         |
| Add Playwright / web-e2e / Vitest coverage for `modules/web` | [web-e2e-ppt056.md](learnings/web-e2e-ppt056.md)                             |
| Add ingest uniqueness / ledger upsert conflict keys          | [ingestion-provenance-sidecar.md](learnings/ingestion-provenance-sidecar.md) |
| Change IngestionRunner ack / DLQ / dry_run semantics         | [ingestor-runner-poison-ack.md](learnings/ingestor-runner-poison-ack.md)     |
