# Learnings index — save-ma-money

Operation-keyed behavioral rules: one lesson per file, fired by trigger, origin `success | failure`. To add one, copy `_TEMPLATE.md` to `<slug>.md`.

<!-- GENERATED at /strata:save from learnings/ frontmatter — do not hand-edit; edit learning files instead -->

| Trigger                                                        | Applies when                                                 | Origin  | File                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------ | ------- | ------------------------------------------------------------------ |
| before changing auth, register, login, users passwords, JWT    | modules/api/\*\*/auth\*, security\*, supabase\*; model users | failure | [supabase-auth-ownership.md](supabase-auth-ownership.md)           |
| before changing local register/login or AUTH_AUTO_CONFIRM      | modules/api/\*\*/supabase\*, auth\*, bff_auth\*; env local   | failure | [local-supabase-email-confirm.md](local-supabase-email-confirm.md) |
| before committing changes under modules/api/src                | modules/api/\*\*                                             | failure | [api-pre-commit-lint.md](api-pre-commit-lint.md)                   |
| before git commit when modules/ or bin/ changed                | modules/\*\*, bin/\*\*                                       | success | [strata-strict-pairing.md](strata-strict-pairing.md)               |
| before adding or wiring modules/ingestor\* packages            | modules/ingestor-core/\*\*, modules/ingestors/\*\*, bin/make | success | [ingestor-scaffold-ci-split.md](ingestor-scaffold-ci-split.md)     |
| before adding ingest uniqueness or ledger upsert conflict keys | modules/model/\*\*/ingestion\*, upsert.py, alembic/\*\*      | success | [ingestion-provenance-sidecar.md](ingestion-provenance-sidecar.md) |
| before parsing DataFrames with optional int/date into DTOs     | modules/model/\*\*/datautils\*, api schemas / list paths     | failure | [pandas-optional-int-nan.md](pandas-optional-int-nan.md)           |
| before wiring or changing /reports endpoints or ReportService  | modules/api/\*\*/reports\*, modules/model/\*\*/reports.py    | success | [report-tenant-scoping.md](report-tenant-scoping.md)               |
| before adding transactions, movements, or bulk create UI       | modules/web/\*\*/transactions\*, movements\*; api/txns/movs  | success | [web-ledger-ui-no-domain.md](web-ledger-ui-no-domain.md)           |
