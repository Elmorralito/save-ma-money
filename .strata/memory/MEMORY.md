# Memory Index — save-ma-money

Pure hot index: live pointers + the generated rules-by-trigger table. Keep ≤80 lines. Structure and routing live in `.strata/MANIFEST.md`, not here.

## Live pointers

- [Project state](project_state.md) — Supabase project owns Auth + user management (PPT-039).
- [Active issues](../issues/ACTIVE.md) — (none; PPT-040 open on #92).
- [Open backlog](../issues/OPEN.md) — PPT-040 B0 CI / Codecov patch; PPT-044 API hardening.

## Rules by trigger

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| When you are about to…                                      | Read                                                               |
| ----------------------------------------------------------- | ------------------------------------------------------------------ |
| Change auth, register, login, users passwords, or JWT issue | [supabase-auth-ownership.md](learnings/supabase-auth-ownership.md) |
| Commit under `modules/api/src`                              | [api-pre-commit-lint.md](learnings/api-pre-commit-lint.md)         |
| Commit when `modules/` or `bin/` changed                    | [strata-strict-pairing.md](learnings/strata-strict-pairing.md)     |
| Wire `/reports/*` or ReportService                          | [report-tenant-scoping.md](learnings/report-tenant-scoping.md)     |
