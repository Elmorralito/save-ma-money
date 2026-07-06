# PPT-031 Design Documents

Design artifacts for [refactor(PPT-031): Simplify #28](https://github.com/Elmorralito/save-ma-money/issues/28).

Issue tracker and merged PR notes: [CHANGELOG.md](../../CHANGELOG.md).

## Document ↔ issue map

| Document                                                                                           | Issue                                                                 | Status                          | Description                                                                                              |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [`../issues/PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md)         | [#28](https://github.com/Elmorralito/save-ma-money/issues/28)         | Active                          | Parent requirements (FR/NFR, tracks A–F)                                                                 |
| [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md)                                                       | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)         | Complete (awaiting G0 sign-off) | As-is schema audit (3NF, handlers, API gaps)                                                             |
| [`../issues/PPT-031-C-supabase-decision-brief.md`](../issues/PPT-031-C-supabase-decision-brief.md) | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)         | Active                          | Supabase × FastAPI decision (B0–B3)                                                                      |
| `PPT-031-v1-schema.md` _(planned)_                                                                 | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | Pending                         | Target schema v1–v3 + ER diagram                                                                         |
| `PPT-031-api-model-mapping.md` _(planned)_                                                         | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)         | Pending                         | Endpoint → DTO → SQLModel mapping                                                                        |
| `PPT-031-migration-runbook.md` _(planned)_                                                         | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)         | Partial                         | Alembic runbook; CI gate exists — see [migration-check.yml](../../.github/workflows/migration-check.yml) |
| `PPT-031-auth-contract.md` _(planned)_                                                             | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E | Pending                         | Auth/register/login/JWT (FR-10, FR-11)                                                                   |

## Platform

**PostgreSQL via Supabase** — DuckDB is out of scope ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

## Progress status (2026-07-06)

| Track | Step                   | Issue                                                                 | Deliverable                                                                              | Progress                                                                                                                                                                    |
| ----- | ---------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A** | A1 — v0 audit          | [#30](https://github.com/Elmorralito/save-ma-money/issues/30)         | [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md)                                             | **Written** — 14-table inventory, 3NF analysis, NF-01–NF-20 register, expert review (10 iterations); awaiting maintainer sign-off                                           |
| **A** | A2 — v1 draft          | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | `PPT-031-v1-schema.md`                                                                   | Not started                                                                                                                                                                 |
| **A** | A3 — v2 (API domain)   | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | `PPT-031-v1-schema.md`                                                                   | Not started — blocked on v1                                                                                                                                                 |
| **A** | A4 — v3 freeze         | [#32](https://github.com/Elmorralito/save-ma-money/issues/32)         | ER diagram + migration outline                                                           | Not started — blocked on v1/v2                                                                                                                                              |
| **B** | Supabase decision      | [#31](https://github.com/Elmorralito/save-ma-money/issues/31)         | [`PPT-031-C-supabase-decision-brief.md`](../issues/PPT-031-C-supabase-decision-brief.md) | Brief written — B0–B3 options documented                                                                                                                                    |
| **C** | API spec realignment   | [#33](https://github.com/Elmorralito/save-ma-money/issues/33)         | `PPT-031-api-model-mapping.md`                                                           | Not started                                                                                                                                                                 |
| **D** | Migration + validation | [#34](https://github.com/Elmorralito/save-ma-money/issues/34)         | `PPT-031-migration-runbook.md`                                                           | **In progress** — CI gate [migration-check.yml](../../.github/workflows/migration-check.yml) runs PostgreSQL upgrade/downgrade + `alembic check`; runbook doc still pending |
| **E** | Auth contract          | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E | `PPT-031-auth-contract.md`                                                               | Not started                                                                                                                                                                 |
| **F** | Reports read model     | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track F | §15 in v0 audit (input only)                                                             | Documented in v0 — full spec pending v3                                                                                                                                     |

**Phase context:** Phase 1 (users + `owner_id`, PR #27) shipped in [#26](https://github.com/Elmorralito/save-ma-money/issues/26). Phase 2 is design-first ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)); implementation ([#25](https://github.com/Elmorralito/save-ma-money/issues/25)) remains blocked until v3 freeze.

## Pending gates

Gates that must clear before downstream work proceeds. Status reflects repo state as of 2026-07-06.

| Gate                                      | Blocks                                                                                                                                               | Status          | Owner action                                                                                                                                                                |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **G0 — v0 audit sign-off**                | Closing [#30](https://github.com/Elmorralito/save-ma-money/issues/30); starting v1 ([#32](https://github.com/Elmorralito/save-ma-money/issues/32))   | **Pending**     | Issue [#30](https://github.com/Elmorralito/save-ma-money/issues/30) closed; review [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md) §12–§14 and confirm G0 on #30               |
| **G0b — v0 hotfix approval** _(optional)_ | Hotfix PR for pre-v3 ingestion on current schema                                                                                                     | **Pending**     | Review [`PPT-031-v0-audit.md` §16](PPT-031-v0-audit.md#16-optional-v0-hotfix-backlog-pre-v3); approve scoped `modules/model` PR (NF-04, NF-13, NF-14, NF-15)                |
| **G1 — v3 schema freeze**                 | [#25](https://github.com/Elmorralito/save-ma-money/issues/25) API CRUD; [#34](https://github.com/Elmorralito/save-ma-money/issues/34) migrations     | **Pending**     | Approve target schema on [#28](https://github.com/Elmorralito/save-ma-money/issues/28) after [#32](https://github.com/Elmorralito/save-ma-money/issues/32) v1→v3 iterations |
| **G2 — Tenancy strategy (FR-02)**         | Closing [#24](https://github.com/Elmorralito/save-ma-money/issues/24); RLS design ([#31](https://github.com/Elmorralito/save-ma-money/issues/31) B3) | **Pending**     | Choose FK-chain vs denormalized `owner_id` vs RLS — decide in v3 doc                                                                                                        |
| **G3 — API ↔ model mapping (FR-07)**      | [#33](https://github.com/Elmorralito/save-ma-money/issues/33); MVP endpoint scope                                                                    | **Pending**     | Produce `PPT-031-api-model-mapping.md`; resolve phantom fields (NF-09)                                                                                                      |
| **G4 — Budgets decision (FR-09)**         | `/budgets/*` in API spec                                                                                                                             | **Pending**     | Add budget entities in v3 or remove from spec                                                                                                                               |
| **G5 — Auth contract (FR-10, FR-11)**     | `/auth/*` routes in [#25](https://github.com/Elmorralito/save-ma-money/issues/25)                                                                    | **Pending**     | Produce `PPT-031-auth-contract.md`                                                                                                                                          |
| **G6 — Legacy data migration (FR-14)**    | `./deploy/alembic.sh upgrade` on pre-#26 dumps                                                                                                       | **In progress** | CI validates fresh PostgreSQL migrations ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)); backfill/runbook doc still pending                                |
| **G7 — Supabase option lock (B0–B3)**     | Env docs, optional RLS ([#31](https://github.com/Elmorralito/save-ma-money/issues/31))                                                               | **Pending**     | Confirm B0/B1 for v3; defer B2/B3 unless chosen                                                                                                                             |
| **G8 — ER diagram refresh (NFR-06)**      | Visual source of truth                                                                                                                               | **Pending**     | Regenerate after v3 migration ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)); current PNG predates `users`                                                 |

### Recommended review order

1. **G0** — Sign off v0 audit ([#30](https://github.com/Elmorralito/save-ma-money/issues/30))
2. **#32** — v1 target schema (decisions: FR-02, FR-05, FR-09, FR-13, FR-15 from v0 §11)
3. **G3, G4, G5** — API mapping, budgets, auth (parallel after v1 draft)
4. **G1** — v3 freeze comment on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
5. **G6, G7, G8** — Migration runbook, Supabase lock, ER diagram ([#34](https://github.com/Elmorralito/save-ma-money/issues/34))

### Optional v0 hotfix review (pre-v3)

If ingestion continues on the current schema before v3, review and optionally implement the **patch backlog** in [`PPT-031-v0-audit.md` §16](PPT-031-v0-audit.md#16-optional-v0-hotfix-backlog-pre-v3) (gate **G0b** below).

| Finding | Severity | Audit section                                              |
| ------- | -------- | ---------------------------------------------------------- |
| NF-04   | Critical | §16.2 — `AccountsIndexerDTO._validate_linked_accounts()`   |
| NF-13   | Critical | §16.3 — `LiabilityAccountsDTO.total_paid` default          |
| NF-14   | Critical | §16.4 — `FinancedAssetAccountsDTO.financing_share` default |
| NF-15   | High     | §16.5 — Types upsert owner scoping                         |

**G0b — v0 hotfix approval** (optional): Blocks hotfix PR merge only — does not block v1 ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)). **Pending.** Owner action: review §16 acceptance tests; approve scoped `modules/model` PR.
