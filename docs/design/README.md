# PPT-031 Design Documents

Design artifacts for [refactor(PPT-031): Simplify #28](https://github.com/Elmorralito/save-ma-money/issues/28) (**closed**).

This directory holds two files:

| File                                 | Role                                                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **Canonical design body** — v0 audit through migration runbook (Parts I–VII)             |
| [`README.md`](README.md)             | **Program index** — issue map, gates (G0–G8), progress, and links into `ARCHITECTURE.md` |

Issue tracker and merged PR notes: [CHANGELOG.md](../../CHANGELOG.md). Monorepo overview and documentation hub: [root README](../../README.md).

## Primary architecture document

**[`ARCHITECTURE.md`](ARCHITECTURE.md)** consolidates the former standalone design files into seven navigable parts:

| Part | Topic                                                                                      | Issue                                                                  |
| ---- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| I    | [v0 data model audit](ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)           | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)          |
| II   | [Target schema v1–v3](ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32)         | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)          |
| III  | [Post-MVP v4 extensions](ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a) | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track A+ |
| IV   | [API ↔ model mapping](ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33)            | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)          |
| V    | [API coverage matrix](ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43)              | [#43](https://github.com/Elmorralito/save-ma-money/issues/43)          |
| VI   | [Auth contract](ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)                    | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E  |
| VII  | [Migration runbook](ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34)              | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)          |

**Merged sources (removed):** `PPT-031-v0-audit.md`, `PPT-031-v1-schema.md`, `PPT-031-v4-extensions.md`, `PPT-031-api-model-mapping.md`, `PPT-033-api-coverage-matrix.md`, `PPT-031-auth-contract.md`, `PPT-031-migration-runbook.md` — content lives in `ARCHITECTURE.md` only.

**Live implementation codemap:** [`.strata/docs/ARCHITECTURE.md`](../../.strata/docs/ARCHITECTURE.md) (code paths, not design authority).

## Related documentation

| Document                                                                             | Scope                                              |
| ------------------------------------------------------------------------------------ | -------------------------------------------------- |
| [`modules/model/README.md`](../../modules/model/README.md)                           | v3 schema, services, handlers, migrations, testing |
| [`modules/api/README.md`](../../modules/api/README.md)                               | REST contract, integration guide, 32 MVP endpoints |
| [`docs/issues/`](../issues/README.md)                                                | Issue-linked requirement briefs                    |
| [`docs/postgres_papita_transactions_v4.png`](../postgres_papita_transactions_v4.png) | ER diagram — v3 core + balance materialized views  |
| [`.agents/AGENTS.md`](../../.agents/AGENTS.md)                                       | Agent and contributor operational guide            |

Legacy API filenames (`API_Endpoints.md.md`, `API_Documentation.md.md`) redirect to [`modules/api/README.md`](../../modules/api/README.md).

## Repo implementation snapshot (2026-07-17)

Design gates and code delivery are tracked separately. Current repo state:

| Area                         | Status                                                                                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **v3 schema & migrations**   | Delivered ([#32](https://github.com/Elmorralito/save-ma-money/issues/32), [#34](https://github.com/Elmorralito/save-ma-money/issues/34)); Alembic upgrade/downgrade validated in CI              |
| **Model layer (PPT-041)**    | Closed ([#51](https://github.com/Elmorralito/save-ma-money/issues/51)) — transfers, reports, account extensions, tenancy guards                                                                  |
| **Design program (PPT-031)** | Closed ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)) — unified in [`ARCHITECTURE.md`](ARCHITECTURE.md)                                                                         |
| **API epic (PPT-032)**       | Children **#43–#50 closed**; epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) open for formal close-out. Operator docs: [`modules/api/README.md`](../../modules/api/README.md) |

Part V in [`ARCHITECTURE.md`](ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43) records the #43-era matrix plus a post-delivery note; `.strata/memory/project_state.md` tracks the active sprint.

## Document ↔ issue map

| Document                                                                                                                       | Issue                                                                                                                                 | Status                                 | Description                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------- |
| [`../issues/README.md#part-i--ppt-031-simplify-requirements-28`](../issues/README.md#part-i--ppt-031-simplify-requirements-28) | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)                                                                         | **Closed**                             | Parent requirements (FR/NFR, tracks A–F)                                                |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part I                                                                                    | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)                                                                         | Complete (awaiting G0 sign-off)        | As-is schema audit (3NF, handlers, API gaps)                                            |
| [`../issues/README.md` Part II](../issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31)                          | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)                                                                         | **Complete — G7 Auth-first supersede** | Supabase × FastAPI — Auth MVP; hosted PG optional                                       |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part II                                                                                   | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)                                                                         | **Implemented — awaiting G1 sign-off** | Target schema v1–v3 + ER diagram + Alembic outline                                      |
| [`../postgres_papita_transactions_v3.svg`](../postgres_papita_transactions_v3.svg)                                             | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)                                                                         | **Written — awaiting G1**              | v3 ER diagram (companion to Part II)                                                    |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part III                                                                                  | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track A+                                                                | **Written**                            | Post-MVP: budgets, splits, recurrence, reconciliation, attachments, import batches, RLS |
| [`../postgres_papita_transactions_v4.svg`](../postgres_papita_transactions_v4.svg)                                             | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track A+                                                                | **Written**                            | v3 + v4 additive ER diagram                                                             |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part IV                                                                                   | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)                                                                         | **Written — awaiting G3**              | Endpoint → Service → DTO → SQLModel mapping; MVP list for #25                           |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part V                                                                                    | [#43](https://github.com/Elmorralito/save-ma-money/issues/43)                                                                         | **Complete**                           | API spec validated against v3 model; 32-endpoint matrix                                 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part VII                                                                                  | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)                                                                         | **Delivered (v3 seed)**                | `a75354933e79` baseline; validate on Docker/Supabase                                    |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) Part VI                                                                                   | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) | **Implemented (Supabase Auth)**        | JWKS verify + provision; local HS256 tests only; refresh/logout via Supabase            |

## Platform

**PostgreSQL only** — Docker Postgres locally (B0); any hosted Postgres in staging/prod (Supabase PG optional). **Supabase = Auth only** for MVP ([#49](https://github.com/Elmorralito/save-ma-money/issues/49)). **DuckDB is deprecated** ([#28](https://github.com/Elmorralito/save-ma-money/issues/28), [#31](https://github.com/Elmorralito/save-ma-money/issues/31), [#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

## Progress status (2026-07-13)

| Track  | Step                   | Issue                                                                                                                                 | Deliverable                                                                                                                                               | Progress                                                                                                                                                       |
| ------ | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A**  | A1 — v0 audit          | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)                                                                         | [Part I](ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)                                                                                       | **Written** — awaiting maintainer G0 sign-off                                                                                                                  |
| **A**  | A2 — v1 draft          | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)                                                                         | [Part II §1](ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32)                                                                                 | **Written**                                                                                                                                                    |
| **A**  | A3 — v2 (API domain)   | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)                                                                         | [Part II §2](ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32)                                                                                 | **Written** — categories, movements→TRANSFER; budgets deferred                                                                                                 |
| **A**  | A4 — v3 freeze         | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)                                                                         | [Part II §3–§6](ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32) + [v3 ER](../postgres_papita_transactions_v3.svg)                            | **Implemented in code** — formal G1 sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28) still pending                                    |
| **B**  | Supabase decision      | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)                                                                         | [`docs/issues/README.md` Part II](../issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31) + [`environments/`](../../environments/README.md) | **Complete — G7 Auth-first supersede**                                                                                                                         |
| **C**  | API spec realignment   | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)                                                                         | [Part IV](ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) + [`modules/api/README.md`](../../modules/api/README.md)                              | **Written — awaiting G3**                                                                                                                                      |
| **C2** | API validation matrix  | [#43](https://github.com/Elmorralito/save-ma-money/issues/43)                                                                         | [Part V](ARCHITECTURE.md#part-v--api-coverage-matrix-ppt-033-43)                                                                                          | **Complete** — unblocks PPT-034+ ([#45](https://github.com/Elmorralito/save-ma-money/issues/45)–[#50](https://github.com/Elmorralito/save-ma-money/issues/50)) |
| **D**  | Migration + validation | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)                                                                         | [Part VII](ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34)                                                                                      | **Delivered** — `a75354933e79`; CI validates upgrade/downgrade                                                                                                 |
| **E**  | Auth contract          | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E / [#49](https://github.com/Elmorralito/save-ma-money/issues/49) | [Part VI](ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e) + Supabase Auth                                                                         | **Delivered** — PPT-039 closed; local HS256 = tests                                                                                                            |
| **F**  | Reports read model     | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track F                                                                 | [Part III §5](ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a)                                                                           | **Written** — v4 materialized views                                                                                                                            |
| **A+** | v4 extensions          | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)                                                                         | [Part III](ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a)                                                                              | **Written** — post-MVP additive schema                                                                                                                         |

**Phase context:** Phase 1 (users + `owner_id`, PR #27) shipped ([#26](https://github.com/Elmorralito/save-ma-money/issues/26)). PPT-031 design is **closed**; **PPT-032** children (#43–#50) and PPT-041 (#51) are **closed** — epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) awaits formal close-out.

## Pending gates

Formal sign-off gates. Code may ship before a gate is marked accepted on [#28](https://github.com/Elmorralito/save-ma-money/issues/28).

| Gate                                      | Blocks                                                                             | Status                      | Owner action                                                                                                                                                                         |
| ----------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **G0 — v0 audit sign-off**                | Closing [#30](https://github.com/Elmorralito/save-ma-money/issues/30)              | **Pending**                 | Review [Part I §12–§14](ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30); confirm G0 on #30                                                                                |
| **G0b — v0 hotfix approval** _(optional)_ | Hotfix PR on pre-v3 schema                                                         | **Pending**                 | Review [Part I §16](ARCHITECTURE.md#16-optional-v0-hotfix-backlog-pre-v3)                                                                                                            |
| **G1 — v3 schema freeze**                 | Formal acceptance of v3 as baseline                                                | **Pending sign-off**        | v3 **implemented** in model + migrations; review [Part II §7](ARCHITECTURE.md#7-sign-off-checklist-g1) and approve on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)  |
| **G2 — Tenancy strategy (FR-02)**         | Closing [#24](https://github.com/Elmorralito/save-ma-money/issues/24); RLS (B3)    | **Pending G1**              | Denormalized `owner_id` on hot tables; RLS deferred — confirm on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)                                                       |
| **G3 — API ↔ model mapping (FR-07)**      | MVP endpoint scope ([#33](https://github.com/Elmorralito/save-ma-money/issues/33)) | **Written — awaiting G3**   | Review [Part IV](ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) + [`modules/api/README.md`](../../modules/api/README.md)                                                  |
| **G4 — Budgets decision (FR-09)**         | `/budgets/*` in API spec                                                           | **Designed (v4.1)**         | [Part III §4.1–4.2](ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a) — post-MVP; confirm phasing on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)   |
| **G5 — Auth contract (FR-10, FR-11)**     | `/auth/*` semantics                                                                | **Superseded by PPT-039**   | [Part VI](ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e) — Supabase Auth MVP; refresh/logout via Supabase                                                                   |
| **G6 — Legacy data migration (FR-14)**    | Pre-#26 dump upgrades                                                              | **v0 path done**            | [Part VII §3](ARCHITECTURE.md#3-v0-migration-path-implemented)                                                                                                                       |
| **G7 — Supabase option lock (B0–B3)**     | Env docs, optional RLS                                                             | **Superseded (Auth-first)** | See [`docs/issues/README.md` Part II](../issues/README.md#g7-supersede-2026-07-13--auth-first); hosted PG optional                                                                   |
| **G8 — ER diagram refresh (NFR-06)**      | Visual source of truth                                                             | **In progress**             | Design-time SVG: [`postgres_papita_transactions_v3.svg`](../postgres_papita_transactions_v3.svg); regenerate PNG after [#34](https://github.com/Elmorralito/save-ma-money/issues/34) |

### Recommended review order

1. **G0** — Sign off v0 audit ([#30](https://github.com/Elmorralito/save-ma-money/issues/30))
2. **G1** — Sign off v3 schema on [#28](https://github.com/Elmorralito/save-ma-money/issues/28) using [Part II §7](ARCHITECTURE.md#7-sign-off-checklist-g1)
3. **G3, G4, G5** — API mapping ([#33](https://github.com/Elmorralito/save-ma-money/issues/33)), v4 budget phasing, auth contract (parallel after G1)
4. **G6, G7, G8** — Migration runbook, Supabase lock, ER diagram

### Optional v0 hotfix review (pre-v3)

If ingestion continues on the legacy schema, review [Part I §16](ARCHITECTURE.md#16-optional-v0-hotfix-backlog-pre-v3) (gate **G0b**).

| Finding | Severity | Audit section                                              |
| ------- | -------- | ---------------------------------------------------------- |
| NF-04   | Critical | §16.2 — `AccountsIndexerDTO._validate_linked_accounts()`   |
| NF-13   | Critical | §16.3 — `LiabilityAccountsDTO.total_paid` default          |
| NF-14   | Critical | §16.4 — `FinancedAssetAccountsDTO.financing_share` default |
| NF-15   | High     | §16.5 — Types upsert owner scoping                         |

**G0b** blocks hotfix PR merge only — does not block v3 implementation ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)).
