# Memory Index — save-ma-money

Pure hot index: live pointers + the generated rules-by-trigger table. Keep ≤80 lines. Structure and routing live in `.strata/MANIFEST.md`, not here.

## Live pointers

- [Project state](project_state.md) — PPT-061 E2E seed landed; PPT-055/054 still in flight; next #121.
- [Active issues](../issues/ACTIVE.md) — PPT-061 [#126] `20260803-05`; PPT-055 [#120] `20260803-04`; PPT-054 [#119] `20260803-02`.
- [Open backlog](../issues/OPEN.md) — PPT-040 Codecov; PPT-043 Redis; later PPT-046 children.
- [Archived](../issues/archive/ARCHIVE.md) — PPT-060 [#125] `20260803-03`; PPT-053 [#118] `20260803-01`.

## Rules by trigger

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| When you are about to…                                      | Read                                                                         |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Change auth, register, login, users passwords, or JWT issue | [supabase-auth-ownership.md](learnings/supabase-auth-ownership.md)           |
| Change local register/login or `AUTH_AUTO_CONFIRM_EMAIL`    | [local-supabase-email-confirm.md](learnings/local-supabase-email-confirm.md) |
| Commit under `modules/api/src`                              | [api-pre-commit-lint.md](learnings/api-pre-commit-lint.md)                   |
| Commit when `modules/` or `bin/` changed                    | [strata-strict-pairing.md](learnings/strata-strict-pairing.md)               |
| Wire `/reports/*` or ReportService                          | [report-tenant-scoping.md](learnings/report-tenant-scoping.md)               |
| Add transactions/movements/bulk UI in `modules/web`         | [web-ledger-ui-no-domain.md](learnings/web-ledger-ui-no-domain.md)           |
| Add or refactor SPA forms / Zod / RHF / mutation errors     | [web-forms-ux-kit.md](learnings/web-forms-ux-kit.md)                         |
