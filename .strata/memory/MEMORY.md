# Memory Index — save-ma-money

Pure hot index: live pointers + the generated rules-by-trigger table. Keep ≤80 lines. Structure and routing live in `.strata/MANIFEST.md`, not here.

## Live pointers

- [Project state](project_state.md) — PPT-038 reports API on `feat/PPT-038`; health probe + PPT-044 brief staged.
- [Active issues](../issues/ACTIVE.md) — PPT-038 reports in progress.
- [Open backlog](../issues/OPEN.md) — PPT-040 tests/CI; PPT-044 API hardening.

## Rules by trigger

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| When you are about to…                      | Read                                                           |
| ------------------------------------------- | -------------------------------------------------------------- |
| Commit under `modules/api/src`              | [api-pre-commit-lint.md](learnings/api-pre-commit-lint.md)     |
| Commit when `modules/` or `deploy/` changed | [strata-strict-pairing.md](learnings/strata-strict-pairing.md) |
| Wire `/reports/*` or ReportService          | [report-tenant-scoping.md](learnings/report-tenant-scoping.md) |
