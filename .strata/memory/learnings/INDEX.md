# Learnings index — save-ma-money

Operation-keyed behavioral rules: one lesson per file, fired by trigger, origin `success | failure`. To add one, copy `_TEMPLATE.md` to `<slug>.md`.

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| Trigger                                                       | Applies when                                                 | Origin  | File                                                     |
| ------------------------------------------------------------- | ------------------------------------------------------------ | ------- | -------------------------------------------------------- |
| before changing auth, register, login, users passwords, JWT   | modules/api/\*\*/auth\*, security\*, supabase\*; model users | failure | [supabase-auth-ownership.md](supabase-auth-ownership.md) |
| before committing changes under modules/api/src               | modules/api/\*\*                                             | failure | [api-pre-commit-lint.md](api-pre-commit-lint.md)         |
| before git commit when modules/ or bin/ changed               | modules/\*\*, bin/\*\*                                       | success | [strata-strict-pairing.md](strata-strict-pairing.md)     |
| before wiring or changing /reports endpoints or ReportService | modules/api/\*\*/reports\*, modules/model/\*\*/reports.py    | success | [report-tenant-scoping.md](report-tenant-scoping.md)     |
