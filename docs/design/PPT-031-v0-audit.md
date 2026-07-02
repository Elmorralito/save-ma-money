# PPT-031 v0 Audit — Current `papita_transactions` Schema

**GitHub issue:** [#30](https://github.com/Elmorralito/save-ma-money/issues/30) · **Parent:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28)  
**Status:** Draft v0 (baseline for v1–v3 design in [#32](https://github.com/Elmorralito/save-ma-money/issues/32))  
**Date:** 2026-07-02

## Document ↔ issue cross-reference

| Related document | Issue |
|------------------|-------|
| [`../issues/PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md) | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — requirements |
| [`../issues/PPT-031-C-supabase-decision-brief.md`](../issues/PPT-031-C-supabase-decision-brief.md) | [#31](https://github.com/Elmorralito/save-ma-money/issues/31) — Supabase |
| `PPT-031-v1-schema.md` *(planned)* | [#32](https://github.com/Elmorralito/save-ma-money/issues/32) — target schema |
| `PPT-031-api-model-mapping.md` *(planned)* | [#33](https://github.com/Elmorralito/save-ma-money/issues/33) — API mapping |
| `PPT-031-migration-runbook.md` *(planned)* | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) — migrations |

---

## 1. Purpose

Document the **as-is** data model before PPT-031 simplification: tables, relationships, normalization violations, repository/handler patterns, dialect risks, and API spec gaps. This audit feeds FR-01–FR-17 and unblocks v1 schema proposals.

---

## 2. Scope

| In scope | Out of scope |
|----------|--------------|
| 14 SQLModel tables in `papita_transactions` | Registrar module (not in workspace; handlers in model) |
| 5 Alembic migrations | Production Supabase deployment |
| DTO / repository / service / handler layers | Full API implementation (#25) |
| `API_Endpoints.md.md` vs model mapping | Budget/report SQL implementation |

---

## 3. Table inventory

Schema: `papita_transactions` (`modules/model/src/papita_txnsmodel/model/contstants.py`)

| # | Table | Base class | PK | `owner_id` | Audit cols (`BaseSQLModel`) |
|---|-------|------------|-----|------------|----------------------------|
| 1 | `users` | `BaseSQLModel` | `id` | — | Yes |
| 2 | `accounts` | `BaseSQLModel` | `id` | NOT NULL, indexed | Yes |
| 3 | `types` | `BaseSQLModel` | `id` | NULLABLE, indexed | Yes |
| 4 | `accounts_indexer` | **`SQLModel` only** | `account_id` | NOT NULL, indexed | **No** |
| 5 | `assets_accounts` | `BaseSQLModel` | `id` | NOT NULL, indexed | Yes |
| 6 | `banking_asset_accounts` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 7 | `real_estate_asset_accounts` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 8 | `trading_asset_accounts` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 9 | `liability_accounts` | `BaseSQLModel` | `id` | NOT NULL, indexed | Yes |
| 10 | `bank_credit_liability_accounts` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 11 | `credit_card_liability_accounts` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 12 | `financed_asset_accounts` | `BaseSQLModel` | `bank_credit_liability_account_id` | NOT NULL | Yes |
| 13 | `identified_transactions` | `BaseSQLModel` | `id` | NOT NULL | Yes |
| 14 | `transactions` | `BaseSQLModel` | `id` | NOT NULL, indexed | Yes |

**Note:** Seed migration (`93420bed0a90`) predates `created_at`/`updated_at` on some tables; later migrations added user columns. Model code expects full `BaseSQLModel` fields on all entities except `accounts_indexer`.

---

## 4. Relationship graph

```
users
 ├── accounts (1:N, cascade delete)
 ├── types (1:N, nullable global types)
 ├── accounts_indexer (1:N)
 ├── assets_accounts, liability_accounts, subtype tables (1:N each)
 ├── identified_transactions (1:N)
 └── transactions (1:N)

accounts (1:1) ── accounts_indexer ── type_id ── types
accounts_indexer ──[0..1 each]──> asset_account_id | liability_account_id |
                                   banking_asset_account_id | real_estate_asset_account_id |
                                   trading_asset_account_id |
                                   bank_credit_liability_account_id | credit_card_liability_account_id

financed_asset_accounts: bank_credit_liability_account_id (PK) → asset_account_id

identified_transactions ── type_id ── types
transactions ── optional identified_transaction_id
transactions ── optional from_account_id / to_account_id ── accounts
```

### 4.1 `AccountsIndexer` FK matrix (central complexity)

File: `modules/model/src/papita_txnsmodel/model/indexers.py`

| FK column | Target table |
|-----------|--------------|
| `account_id` | `accounts` (PK) |
| `type_id` | `types` |
| `owner_id` | `users` |
| `asset_account_id` | `assets_accounts` |
| `liability_account_id` | `liability_accounts` |
| `banking_asset_account_id` | `banking_asset_accounts` |
| `real_estate_asset_account_id` | `real_estate_asset_accounts` |
| `trading_asset_account_id` | `trading_asset_accounts` |
| `bank_credit_liability_account_id` | `bank_credit_liability_accounts` |
| `credit_card_liability_account_id` | `credit_card_liability_accounts` |

**Constraint gap:** No CHECK enforcing exactly one subtype FK populated per row.

---

## 5. Normalization analysis

### 5.1 First normal form (1NF)

| Item | Status | Notes |
|------|--------|-------|
| Atomic columns | Mostly OK | `tags` stored as PostgreSQL `ARRAY(String)` on `accounts`, `types`, `identified_transactions` |
| Repeating groups | OK | No repeating column groups |
| **Risk** | ARRAY on DuckDB | No native PG array; dialect parity unverified (NFR-02) |

**Recommendation (v1):** Document ARRAY as acceptable 1NF exception or normalize to `entity_tags` junction table if tag queries become hot paths.

### 5.2 Second normal form (2NF)

| Table | PK | Issue |
|-------|-----|-------|
| `financed_asset_accounts` | `bank_credit_liability_account_id` only | `asset_account_id` and `owner_id` are not part of PK; if one credit finances one asset, OK; if many-to-many needed, PK is wrong (FR-16) |
| All others | Single-column UUID PKs | No partial-key dependencies |

### 5.3 Third normal form (3NF) — primary violations

| ID | Violation | Tables | Transitive dependency |
|----|-----------|--------|------------------------|
| **3NF-01** | Redundant `owner_id` | ~12 child tables | `owner_id` derivable via `accounts.owner_id` or FK chains |
| **3NF-02** | Sparse polymorphic hub | `accounts_indexer` | Type/subtype routing duplicates data reachable via account + discriminator |
| **3NF-03** | Global vs scoped types | `types` | `name` globally UNIQUE while `owner_id` nullable — mixed global/user semantics |
| **3NF-04** | Join table owner | `financed_asset_accounts` | `owner_id` derivable from linked asset/liability owners |
| **3NF-05** | Transaction owner | `transactions` | `owner_id` derivable from `from_account_id` or `to_account_id` (when set) |

### 5.4 Intentional denormalizations to evaluate (not yet approved)

| Candidate | Rationale for keeping | Rationale for removing |
|-----------|----------------------|------------------------|
| `transactions.owner_id` | Fast tenant-filtered ledger queries | FK chain via accounts |
| `owner_id` on subtype tables | Avoid joins in ingestion pipeline | Single source on `accounts` |
| Deterministic UUIDs in DTOs | Idempotent loads | Must include tenant namespace (FR-15) |

---

## 6. Identity & tenancy (FR-02, FR-15)

### 6.1 `Users`

- Fields: `username`, `email`, `password` (hashed on DTO serialize)
- ID: deterministic `uuid5(NAMESPACE_URL, sha256(username))` in `UsersDTO`
- Service: `UsersService.get_owner()` only — **no `verify_credentials`** (FR-10)

### 6.2 `Types` — global vs user-scoped

| Aspect | Behavior | Risk |
|--------|----------|------|
| `owner_id` | Nullable (global types allowed) | Read merges global + owned (`TypesRepository.get_records`) |
| `name` | **Globally unique** | User A cannot create type same name as global/user B |
| ID generation | `uuid5(sha256(name + classification))` — **ignores owner_id** | Cross-tenant UUID collision (FR-15) |
| Write scoping | `TypesRepository` extends `BaseRepository`, not `OwnedTableRepository` | Weaker write-path tenant enforcement |

### 6.3 `OwnedTableRepository` pattern

Used by: accounts, assets, liabilities, indexers, transactions repositories.

- Injects `owner_id` on upsert/get when `owner=` provided
- Handlers/services still accept `owner=None` (legacy path) — **tenant bypass on load** (FR-14)

---

## 7. Layer impact surface (FR-03, FR-08)

### 7.1 Handlers (registrar integration point)

File: `modules/model/src/papita_txnsmodel/handlers/`

| Handler | Registry labels (sample) | Services |
|---------|-------------------------|----------|
| `AccountsTableHandler` | `accounts`, `accounts_table` | `AccountsService` |
| `AssetAccountsTableHandler` | `asset_accounts`, `assets` | `AssetAccountsService` |
| `LiabilityAccountsTableHandler` | `liability_accounts` | `LiabilityAccountsService` |
| `AccountsIndexerTableHandler` | `accounts_indexer`, `accounts_indexer_table` | `AccountsIndexerService` + linked services |
| `IdentifiedTransactionsTableHandler` | (transactions module) | `IdentifiedTransactionsService` |
| `TransactionsTableHandler` | (transactions module) | `TransactionsService` |
| `TypesTableHandler` | (types module) | `TypesService` |

**v3 impact:** Indexer removal/redesign touches `handlers/accounts.py`, `handlers/factory.py`, and all `AccountsIndexerService` consumers.

### 7.2 Services — linker pattern

| Module | Pattern |
|--------|---------|
| `services/indexers.py` | `AccountsIndexerService` + 7 `LinkedEntity` bindings |
| `services/extends.py` | `TypedLinkedEntitiesServiceMixin`, `LinkedEntitiesService` |
| `services/assets.py` | `FinancedAssetAccountsService` |
| `services/transactions.py` | Links to `IdentifiedTransactions` |

**v3 impact:** `extends.py` mixin graph must be redesigned with indexer simplification.

### 7.3 DTO validation hotspots

| DTO | File | Issue |
|-----|------|-------|
| `AccountsIndexerDTO` | `access/indexers/dto.py` | Validates sparse FK matrix |
| `TypesDTO` | `access/types/dto.py` | ID hash ignores owner |
| `UsersDTO` | `access/users/dto.py` | Password hash requires uninitialized factory |
| `FinancedAssetAccountsDTO` | `access/assets/dto.py` | `financing_share` default 0.0 vs `gt=0` |

---

## 8. Migration history

| Revision | Date | Summary |
|----------|------|---------|
| `93420bed0a90` | 2025-10-14 | Seed: all core tables + FKs (Postgres) |
| `53fec3d56681` | 2026-01-28 | New fields |
| `06b97dfcb5c7` | 2026-01-28 | **`users` table + `owner_id NOT NULL` on ~13 tables** — no backfill |
| `255bb7382571` | 2026-01-30 | `types.owner_id` nullable + FK |
| `ccaa69123f7e` | 2026-01-30 | Drop `password_salt`, `token_salt` from users |

**Legacy data risk (FR-14):** Upgrading pre-#26 DuckDB/Postgres dumps fails when existing rows lack `owner_id`.

---

## 9. Database platform (updated 2026-07-02)

**Target:** PostgreSQL via **Supabase**. DuckDB is **out of scope** for PPT-031 migration work ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

| Topic | PostgreSQL (Supabase) | Notes |
|-------|----------------------|-------|
| FK integrity | Full ER expected | Validates simplified v3 schema |
| `ARRAY` columns | Native | Tags on `accounts`, `types`, `identified_transactions` |
| Upsert | `PostgreSQLUpserter` | Test on Postgres only |
| RLS | Supported (optional B3) | See [#31](https://github.com/Elmorralito/save-ma-money/issues/31) |
| ~~DuckDB~~ | **Deprecated** | [#17](https://github.com/Elmorralito/save-ma-money/issues/17) superseded |

### Legacy dialect notes (historical — pre-Supabase decision)

Prior audit referenced DuckDB dual-dialect risks (`DuckDBUpserter`, FK gaps #17, `.data/store.duckdb`). These are **no longer in scope** for Track D.

---

## 10. API spec vs model gaps (FR-07, FR-13, FR-17)

Canonical spec: `modules/api/API_Endpoints.md.md` (43+ operations). Secondary: `API_Documentation.md.md`.

| API resource | Model mapping | Gap severity |
|--------------|---------------|--------------|
| `/accounts/*` | `accounts` + indexer + subtypes | **High** — spec adds `balance`, `currency`, `initial_balance`, flat `account_type` |
| `/categories/*` | `types` | **High** — `income/expense`, `parent_id`, hierarchy vs flat `TypesClassifications` |
| `/transactions/*` | `transactions` | **High** — spec fields: `transaction_type`, `category_id`, `status`, `currency`; model has `value`, accounts, optional template FK |
| `/movements/*` | ~`transactions` | **Medium** — undefined domain term |
| `/budgets/*` | **none** | **Critical** — full CRUD with no table |
| `/reports/*` | **none** | **High** — aggregation layer missing; `budget-performance` depends on budgets |
| `/auth/*` | `users` | **High** — `full_name` vs `username`; refresh/logout vs stateless JWT |

---

## 11. Security & auth audit (FR-10, FR-11, NFR-08)

| Component | Status |
|-----------|--------|
| `AuthSecurityManager` | JWT encode/decode only |
| `UsersService.verify_credentials` | **Missing** |
| `PasswordManagerFactory` bootstrap | **Not called** before DTO serialize |
| JWT refresh/logout | Spec'd, not designed |
| Cross-tenant tests | **None** (NFR-04) |

---

## 12. Test coverage snapshot (NFR-04, NFR-09)

| Area | Tests exist? | Path |
|------|--------------|------|
| Base repository | Yes (mocked) | `tests/.../access/base/test_repository.py` |
| Connector | Yes | `tests/.../database/test_connector.py` |
| Upsert | Yes | `tests/.../database/test_upsert.py` |
| Users / auth / hashutils | **No** | — |
| Indexers / handlers | **No** | — |
| Cross-tenant denial | **No** | — |
| Alembic dual-dialect | **No CI gate** | `.github/workflows/quality-control.yml` |
| API module tests | **Path configured, dir missing** | root `pyproject.toml` |

---

## 13. v1 design recommendations (input to #32)

Priority-ordered directions for schema iteration:

1. **Replace `AccountsIndexer`** with `accounts.account_kind` enum + single optional extension FK (FR-03).
2. **Resolve tenancy** — pick FK-chain vs denormalized `owner_id` vs RLS; fix `Types` ID/uniqueness (FR-02, FR-15).
3. **Consolidate subtype tables** where column overlap >70% (FR-04).
4. **Clarify transaction model** — keep template/posted split; expose in API explicitly (FR-05).
5. **Fix `financed_asset_accounts` PK** and owner consistency checks (FR-16).
6. **Legacy migration** — default user seed + backfill script (FR-14).
7. **Defer budgets/reports** from MVP or add read-model tables (FR-09, FR-12).

---

## 14. Requirement traceability

| Audit finding | Requirement |
|---------------|-------------|
| 3NF-01..05 | FR-01, FR-02 |
| AccountsIndexer | FR-03, FR-06 (no BaseSQLModel) |
| Subtype explosion | FR-04 |
| Template vs posted | FR-05 |
| API phantom fields | FR-07, FR-13, FR-17 |
| Auth gaps | FR-10, FR-11, NFR-08 |
| Reports/budgets | FR-09, FR-12 |
| Legacy owner_id | FR-14 |
| Types collision | FR-15 |
| Financed assets PK | FR-16 |
| DuckDB/upsert/CI | NFR-02, NFR-07, NFR-09, NFR-10 (Postgres/Supabase only) |
| Version drift | NFR-11 |

---

## 15. References

- Issue: [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
- Requirements: `docs/issues/PPT-031-simplify-requirements.md`
- ER (stale): `docs/postgres_papita_transactions.png`
- Migrations: `modules/model/alembic/versions/`
- Handlers: `modules/model/src/papita_txnsmodel/handlers/`

---

## 16. Sign-off

- [ ] Maintainer review of normalization findings
- [ ] v1 schema draft opened in [#32](https://github.com/Elmorralito/save-ma-money/issues/32)
- [ ] API mapping draft opened in [#33](https://github.com/Elmorralito/save-ma-money/issues/33)
