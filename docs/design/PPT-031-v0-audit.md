# PPT-031 v0: Data Model Audit and 3NF Gap Analysis

| Field | Value |
| --- | --- |
| **Issue** | [#30 — Data model audit and 3NF gap analysis (v0)](https://github.com/Elmorralito/save-ma-money/issues/30) |
| **Parent** | [#28 — refactor/PPT-031: Simplify data model and align API design](https://github.com/Elmorralito/save-ma-money/issues/28) |
| **Track** | A — Step A1 |
| **Baseline** | PR #27 (users + `owner_id`), PR #29 (API spec scaffold) |
| **Schema** | `papita_transactions` (PostgreSQL / Supabase) |
| **Date** | 2026-07-05 |
| **Status** | v0 baseline — pre-simplification |

---

## 1. Executive summary

This document captures the **current state** of the `papita_transactions` schema before PPT-031 simplification. It inventories all 14 SQLModel tables, analyzes normalization (1NF / 2NF / 3NF), assesses `AccountsIndexer` complexity, evaluates redundant `owner_id` columns introduced in PR #27, and documents how repositories, handlers, and the load pipeline interact with the schema today.

**Key findings:**

| Area | Finding | Severity |
| --- | --- | --- |
| **AccountsIndexer** | 8 nullable FK columns with no DB constraint enforcing exactly one populated | High |
| **Redundant `owner_id`** | Present on 13 tables; derivable via FK chains in most cases | Medium |
| **3NF violations** | Transitive dependencies via duplicated financial columns across base + subtype tables; denormalized tenancy | Medium–High |
| **Types identity** | Deterministic UUID ignores `owner_id`; `name` is globally unique | High (multi-tenant) |
| **AccountsIndexer audit gap** | Does not extend `BaseSQLModel` — no soft delete or timestamps | Medium |
| **Load pipeline** | Deep dependency chains through indexer handler; `owner=None` still accepted | Medium |

The v0 schema is **functional for single-tenant ingestion** but carries structural debt that blocks clean API CRUD (#25) and multi-tenant isolation (#24) without redesign (#32).

---

## 2. Schema overview

### 2.1 Relationship sketch

```
users
  └── owner_id on ~13 tables (PR #27)
accounts (owner_id)
  └── accounts_indexer (owner_id, type_id, 8 nullable subtype FKs)
        ├── assets_accounts | liability_accounts
        ├── banking_asset_accounts | real_estate_asset_accounts | trading_asset_accounts
        └── bank_credit_liability_accounts | credit_card_liability_accounts
financed_asset_accounts (join: bank_credit ↔ asset, financing_share)
identified_transactions (owner_id, type_id)
  └── transactions (owner_id, optional from/to account FKs, optional template FK)
types (nullable owner_id — global or user-scoped)
```

### 2.2 ER reference

Existing diagram (predates `users` and PR #27 changes): [`docs/postgres_papita_transactions.png`](../postgres_papita_transactions.png). Regenerate after v3 migration (#34).

### 2.3 Base model inheritance

| Pattern | Tables |
| --- | --- |
| Extends `BaseSQLModel` | 13 tables — `active`, `deleted_at`, `created_at`, `updated_at` |
| Raw `SQLModel` (no audit fields) | `accounts_indexer` only |

Source: [`modules/model/src/papita_txnsmodel/model/base.py`](../../modules/model/src/papita_txnsmodel/model/base.py), [`indexers.py`](../../modules/model/src/papita_txnsmodel/model/indexers.py).

---

## 3. Table inventory

All tables live in schema **`papita_transactions`**. Index names follow Alembic convention `ix_papita_transactions_<table>_<column>`.

### 3.1 `users`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `username` | VARCHAR | NO | unique |
| `email` | VARCHAR | NO | unique |
| `password` | VARCHAR | NO | Argon2 hash at DTO serialize time |
| `active` | BOOLEAN | NO | default `true` |
| `deleted_at` | TIMESTAMP | YES | soft delete |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**PK:** `id`

**FKs:** none (tenant root)

**Indexes:** `id`, `username` (unique), `email` (unique)

**Model:** [`model/users.py`](../../modules/model/src/papita_txnsmodel/model/users.py)

---

### 3.2 `accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK, auto-generated |
| `name` | VARCHAR | NO | |
| `description` | TEXT | NO | |
| `tags` | VARCHAR[] | NO | min 1, unique items (Pydantic) |
| `start_ts` | TIMESTAMP | NO | indexed |
| `end_ts` | TIMESTAMP | YES | indexed |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`

**Indexes:** `name`, `start_ts`, `end_ts`, `owner_id`

---

### 3.3 `types`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK; deterministic uuid5 from `name + classification` in DTO |
| `classification` | ENUM | NO | `ASSETS`, `LIABILITIES`, `TRANSACTIONS` |
| `name` | VARCHAR | NO | **globally unique** |
| `tags` | VARCHAR[] | NO | |
| `description` | TEXT | NO | |
| `owner_id` | UUID | YES | FK → `users.id`; NULL = global type |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id` (nullable since migration `255bb7382571`)

**Indexes:** `classification`, `name` (unique), `owner_id`

---

### 3.4 `accounts_indexer`

Central polymorphic hub — **does not extend `BaseSQLModel`**.

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `account_id` | UUID | NO | PK; FK → `accounts.id` |
| `type_id` | UUID | NO | FK → `types.id` |
| `owner_id` | UUID | NO | FK → `users.id` (PR #27) |
| `asset_account_id` | UUID | YES | FK → `assets_accounts.id` |
| `liability_account_id` | UUID | YES | FK → `liability_accounts.id` |
| `banking_asset_account_id` | UUID | YES | FK → `banking_asset_accounts.id` |
| `real_estate_asset_account_id` | UUID | YES | FK → `real_estate_asset_accounts.id` |
| `trading_asset_account_id` | UUID | YES | FK → `trading_asset_accounts.id` |
| `bank_credit_liability_account_id` | UUID | YES | FK → `bank_credit_liability_accounts.id` |
| `credit_card_liability_account_id` | UUID | YES | FK → `credit_card_liability_accounts.id` |

**PK:** `account_id` (1:1 with `accounts`)

**FKs:** 9 outbound FKs (account, type, owner, 6 subtype columns)

**Indexes:** `type_id`, `owner_id`

**Missing vs other tables:** no `active`, `deleted_at`, `created_at`, `updated_at`

---

### 3.5 `assets_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `months_per_period` | SMALLINT | NO | default 1, > 0 |
| `initial_value` | DECIMAL(22,8) | YES | > 0 |
| `last_value` | DECIMAL(22,8) | YES | > 0 |
| `monthly_interest_rate` | DECIMAL(10,4) | YES | > 0 |
| `yearly_interest_rate` | DECIMAL(10,4) | YES | > 0 |
| `roi` | DECIMAL(10,4) | YES | > 0 |
| `periodical_earnings` | DECIMAL(22,8) | YES | > 0 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.asset_account_id`, `financed_asset_accounts.asset_account_id`

**Indexes:** `owner_id`

---

### 3.6 `banking_asset_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK (extends `ExtendedAssetAccounts`) |
| `entity` | VARCHAR | NO | bank name |
| `account_number` | VARCHAR | YES | |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.banking_asset_account_id`

**Indexes:** `entity`, `account_number`

---

### 3.7 `real_estate_asset_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `address`, `city`, `country` | VARCHAR | NO | |
| `total_area`, `built_area` | DECIMAL(12,4) | NO | > 0 |
| `area_unit` | ENUM | NO | `SQ_MT`, `SQ_FT`, `AC`, `HA`, `BLK` |
| `ownership` | ENUM | NO | `FULL`, `PARTIAL` |
| `participation` | DECIMAL(4,4) | NO | 0–1, default 1.0 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.real_estate_asset_account_id`

**Indexes:** none beyond PK

---

### 3.8 `trading_asset_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `buy_value` | DECIMAL(22,8) | NO | > 0 |
| `last_value` | DECIMAL(22,8) | YES | > 0 |
| `units` | SMALLINT | NO | default 1, > 0 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.trading_asset_account_id`

**Indexes:** none beyond PK

**Note:** `last_value` duplicated conceptually with `assets_accounts.last_value` when both rows exist for the same logical account.

---

### 3.9 `liability_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `months_per_period` | SMALLINT | YES | default 1 |
| `initial_value`, `present_value` | DECIMAL(22,8) | NO | > 0 |
| `monthly_interest_rate`, `yearly_interest_rate` | DECIMAL(10,4) | YES | > 0 |
| `payment`, `total_paid` | DECIMAL(22,8) | NO | > 0 |
| `overall_periods`, `periods_paid` | SMALLINT | NO | > 0 |
| `closing_day` | SMALLINT | NO | 1–28 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.liability_account_id`

**Indexes:** `owner_id`

**Doc drift:** model docstring references `account_id` / `type_id` fields that **do not exist** on the DAO.

---

### 3.10 `bank_credit_liability_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `paid` | BOOLEAN | NO | default false |
| `insurance_payment`, `extras_payment` | DECIMAL(22,8) | NO | |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.bank_credit_liability_account_id`, `financed_asset_accounts.bank_credit_liability_account_id`

**Indexes:** none beyond PK

---

### 3.11 `credit_card_liability_accounts`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `credit_limit` | DECIMAL(22,8) | NO | |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.credit_card_liability_account_id`

**Indexes:** none beyond PK

---

### 3.12 `financed_asset_accounts`

Join table linking bank credit liabilities to assets.

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `bank_credit_liability_account_id` | UUID | NO | PK; FK → `bank_credit_liability_accounts.id` |
| `asset_account_id` | UUID | NO | FK → `assets_accounts.id` |
| `financing_share` | DECIMAL(4,4) | NO | 0–1, default 1.0 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `bank_credit_liability_account_id` only — **one credit → one asset**; one asset may have many credits only if PK design changes.

**FKs:** both account FKs + `owner_id` → `users.id`

**Indexes:** none beyond PK

**Integrity gaps:** no CHECK that asset, liability, and join `owner_id` values match; no constraint that financing shares sum to 1.0 per asset.

---

### 3.13 `identified_transactions`

Transaction templates / recurring plans.

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `type_id` | UUID | NO | FK → `types.id` |
| `name` | VARCHAR | NO | indexed |
| `tags` | VARCHAR[] | NO | |
| `description` | VARCHAR | NO | |
| `planned_value` | DECIMAL(22,8) | NO | > 0 |
| `planned_transaction_day` | SMALLINT | NO | 1–28 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** `type_id` → `types.id`, `owner_id` → `users.id`

**Indexes:** `name`

---

### 3.14 `transactions`

Posted ledger entries.

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | PK |
| `identified_transaction_id` | UUID | YES | FK → `identified_transactions.id` |
| `from_account_id` | UUID | YES | FK → `accounts.id` |
| `to_account_id` | UUID | YES | FK → `accounts.id` |
| `transaction_ts` | TIMESTAMP | NO | indexed |
| `value` | DECIMAL(22,8) | NO | > 0 |
| `owner_id` | UUID | NO | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | — | — | BaseSQLModel |

**PK:** `id`

**FKs:** three optional/required FKs + `owner_id` → `users.id`

**Indexes:** `transaction_ts`, `owner_id`

**Business rule (handler-enforced):** exactly one of `from_account_id` or `to_account_id` must be non-null (income vs expense).

---

## 4. Normalization analysis

### 4.1 First normal form (1NF)

| Table | 1NF status | Notes |
| --- | --- | --- |
| All 14 tables | **Pass** | Atomic scalar columns; `tags` stored as PostgreSQL `ARRAY(String)` |

**1NF consideration — `tags` arrays:**

- Stored as multi-value arrays on `accounts`, `types`, `identified_transactions`.
- Acceptable as 1NF if treated as atomic multi-value attributes, but **not query-friendly** for tag-based filters without `unnest()` or GIN indexes.
- v3 decision needed: keep arrays vs junction table `entity_tags(entity_type, entity_id, tag)`.

**Example:** Two accounts tagged `"primary"` require `WHERE 'primary' = ANY(tags)` — no normalized tag index today.

---

### 4.2 Second normal form (2NF)

2NF applies when a non-key column depends on **part of** a composite primary key.

| Table | 2NF status | Analysis |
| --- | --- | --- |
| Single-column PK tables (12) | **Pass** | No partial key dependencies |
| `accounts_indexer` | **Pass** | PK is `account_id` only |
| `financed_asset_accounts` | **Review** | PK is only `bank_credit_liability_account_id`. `asset_account_id` and `financing_share` depend on the full relationship `(credit_id, asset_id)`. If many-to-many is intended, PK should be composite. |

**Example — financed assets:**

```
financed_asset_accounts
  PK: bank_credit_liability_account_id  ← only credit side in key
  asset_account_id, financing_share     ← logically depend on BOTH credit AND asset
```

If one asset is financed by two credits, the current PK prevents a second row with the same credit ID but **allows ambiguity** about whether multiple credits per asset are modeled correctly.

---

### 4.3 Third normal form (3NF)

3NF requires no transitive dependencies: non-key columns must depend only on the primary key, not on other non-key columns.

#### 4.3.1 Redundant `owner_id` (transitive tenancy)

**Violation pattern:** `owner_id` on child tables when ownership is derivable through FK chains.

| Table | `owner_id` derivable via | Redundant? |
| --- | --- | --- |
| `accounts_indexer` | `account_id` → `accounts.owner_id` | Yes |
| `assets_accounts` | `accounts_indexer.account_id` → `accounts.owner_id` | Yes |
| `banking_asset_accounts` | same chain via indexer | Yes |
| `real_estate_asset_accounts` | same | Yes |
| `trading_asset_accounts` | same | Yes |
| `liability_accounts` | same | Yes |
| `bank_credit_liability_accounts` | same | Yes |
| `credit_card_liability_accounts` | same | Yes |
| `financed_asset_accounts` | either FK side → indexer → accounts | Yes |
| `transactions` | `from_account_id` or `to_account_id` → `accounts.owner_id` | Mostly yes* |
| `identified_transactions` | `type_id` → `types.owner_id` (when not global) | Partial** |
| `types` | self — tenant root for taxonomy | No (when used as scope key) |
| `accounts` | self | No |

\*Income/expense transactions have one account FK populated; `owner_id` duplicates that account's owner.

\*\*Global types (`owner_id IS NULL`) break the derivation chain for `identified_transactions`.

**Concrete example — transaction redundancy:**

```
User A (id: aaa)
  Account "Checking" (owner_id: aaa)
    Transaction T: from_account_id → Checking, owner_id: aaa

If Checking.owner_id changes (account transfer — not supported today):
  - accounts.owner_id updated
  - transactions.owner_id stale → cross-tenant leak or orphan
```

No DB trigger enforces `transactions.owner_id = accounts.owner_id`.

#### 4.3.2 Duplicated financial attributes (subtype overlap)

**Violation:** Base and extended asset/liability tables repeat overlapping financial semantics.

| Base column (`assets_accounts`) | Also on subtype | Transitive dependency |
| --- | --- | --- |
| `last_value` | `trading_asset_accounts.last_value` | Subtype value may diverge from base |
| `initial_value`, interest rates, `roi` | — | Base holds generic attrs; subtype adds specifics without FK to base row |

A banking account row in v0 requires **three physical rows**: `accounts`, `assets_accounts`, `banking_asset_accounts`, linked through `accounts_indexer`. Financial columns on `assets_accounts` are **functionally determined by account identity** but stored separately from subtype-specific columns — classic class-table inheritance overhead, not strictly a 3NF violation, but creates **update anomalies** when `last_value` must stay in sync across base and trading extension.

**Concrete example:**

```
accounts_indexer row for "Brokerage":
  asset_account_id        → assets_accounts (last_value = 10000)
  trading_asset_account_id → trading_asset_accounts (last_value = 10500)

Which is authoritative? No constraint prevents divergence.
```

#### 4.3.3 `AccountsIndexer.type_id` redundancy

`type_id` on `accounts_indexer` is derivable from which subtype FK is populated (asset vs liability) plus the linked `types.classification`. The `AccountsIndexerService` enforces consistency at write time, but the DB does not.

#### 4.3.4 Types global uniqueness vs tenant scope

**Violation (business 3NF / domain normalization):**

- `TypesDTO._normalize_model()` hashes `name + classification` **without `owner_id`**.
- DB enforces `UNIQUE(name)` globally.
- Two tenants creating type `"Groceries"` produce the **same UUID** and collide on insert.

```python
# access/types/dto.py — owner_id excluded from ID hash
self.id = uuid.uuid5(
    uuid.NAMESPACE_URL,
    hashlib.sha256(f"{self.name}_{self.classification.value}".encode()).hexdigest(),
)
```

This is a **cross-tenant identity collision**, not classical 3NF, but violates normalized tenant isolation (FR-15).

---

### 4.4 Normalization summary matrix

| Table | 1NF | 2NF | 3NF | Primary issue |
| --- | --- | --- | --- | --- |
| `users` | ✓ | ✓ | ✓ | — |
| `accounts` | ✓ | ✓ | ✓ | — |
| `types` | ✓ | ✓ | △ | Global unique `name` + nullable `owner_id` |
| `accounts_indexer` | ✓ | ✓ | ✗ | Redundant `owner_id`, `type_id`; sparse FK matrix |
| `assets_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id`; overlaps with subtypes |
| `banking_asset_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id` |
| `real_estate_asset_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id` |
| `trading_asset_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id`; `last_value` overlap |
| `liability_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id` |
| `bank_credit_liability_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id` |
| `credit_card_liability_accounts` | ✓ | ✓ | ✗ | Redundant `owner_id` |
| `financed_asset_accounts` | ✓ | △ | ✗ | PK design; redundant `owner_id` |
| `identified_transactions` | ✓ | ✓ | △ | `owner_id` partially derivable |
| `transactions` | ✓ | ✓ | ✗ | Redundant `owner_id` |

**Legend:** ✓ compliant, ✗ violation, △ partial / context-dependent

---

## 5. `AccountsIndexer` complexity assessment

### 5.1 Sparse FK matrix

The indexer holds **8 nullable FK columns** representing subtype rows. Design intent: exactly **one base** FK (`asset_account_id` XOR `liability_account_id`) and **at most one extended** FK populated.

| FK column | Target table | Layer |
| --- | --- | --- |
| `asset_account_id` | `assets_accounts` | Base asset |
| `liability_account_id` | `liability_accounts` | Base liability |
| `banking_asset_account_id` | `banking_asset_accounts` | Asset extension |
| `real_estate_asset_account_id` | `real_estate_asset_accounts` | Asset extension |
| `trading_asset_account_id` | `trading_asset_accounts` | Asset extension |
| `bank_credit_liability_account_id` | `bank_credit_liability_accounts` | Liability extension |
| `credit_card_liability_account_id` | `credit_card_liability_accounts` | Liability extension |

**Database enforcement:** none. PostgreSQL accepts rows with 0, 2, or all 8 FKs populated.

### 5.2 Application-layer enforcement

| Layer | Enforcement mechanism |
| --- | --- |
| **DTO** | `AccountsIndexerDTO._validate_accounts()` — XOR asset/liability |
| **DTO** | `_validate_extended_accounts()` — at most one extended type |
| **DTO** | `_validate_linked_accounts()` — extended type matches base (note: logic appears inverted in edge cases — raises when extended IS set) |
| **Service** | `AccountsIndexerService.create()` — type classification must match asset vs liability |
| **Service** | `TypedLinkedEntitiesServiceMixin` — cascades `get_or_create` across 7 linked services |

Source: [`access/indexers/dto.py`](../../modules/model/src/papita_txnsmodel/access/indexers/dto.py), [`services/indexers.py`](../../modules/model/src/papita_txnsmodel/services/indexers.py).

### 5.3 Handler dependency graph

`AccountsIndexerTableHandler` wires **8 service dependencies**:

```
AccountsIndexerTableHandler
  ├── AccountsService          (account)
  ├── AssetAccountsService     (asset_account)
  ├── RealEstateAssetAccountsService
  ├── TradingAssetAccountsService
  ├── LiabilityAccountsService (liability_account)
  ├── BankCreditLiabilityAccountsService
  ├── CreditCardLiabilityAccountsService
  └── TypesService             (type)
```

Source: [`handlers/accounts.py`](../../modules/model/src/papita_txnsmodel/handlers/accounts.py) — `AccountsIndexerTableHandler._validate()`.

Each `load()` → `build_record()` may cascade **8 sequential get_or_create** calls per row.

### 5.4 Query cost to resolve a full account

Typical read path for "get account with subtype details":

```sql
-- Minimum joins for a banking asset account
SELECT *
FROM papita_transactions.accounts a
JOIN papita_transactions.accounts_indexer idx ON idx.account_id = a.id
JOIN papita_transactions.assets_accounts aa ON aa.id = idx.asset_account_id
JOIN papita_transactions.banking_asset_accounts ba ON ba.id = idx.banking_asset_account_id
JOIN papita_transactions.types t ON t.id = idx.type_id
WHERE a.id = :account_id AND a.owner_id = :owner_id;
```

**4–5 joins** for a single account list item. Listing all accounts for a user requires the same join pattern or N+1 through `AccountsIndexerService.get(include_linked_dtos=True)`.

### 5.5 Complexity scorecard

| Dimension | Rating (1–5) | Notes |
| --- | --- | --- |
| Schema comprehension | 5 | New developers must learn polymorphic hub pattern |
| Write-path complexity | 5 | 8-dependency handler + DTO validators |
| Read-path complexity | 4 | Multi-join or service-side linked DTO hydration |
| DB integrity | 1 | No CHECK constraints on FK matrix |
| Migration risk | 5 | Central hub — any v3 change touches all account subtypes |
| Test surface | 4 | Combinatorial subtype × validation paths |

**Recommendation (for #32):** Replace with discriminator + single extension FK, or consolidated `accounts` row with `account_kind` enum (per FR-03, FR-04).

---

## 6. Redundant `owner_id` analysis (post PR #27)

PR #27 ([`06b97dfcb5c7`](../../modules/model/alembic/versions/2026_01_28_1921-06b97dfcb5c7_adding_user_table_and_owner_columns.py)) added `owner_id NOT NULL` to 12 child tables plus created `users`. Migration `255bb7382571` later made `types.owner_id` nullable for global types.

### 6.1 Coverage matrix

| Table | Has `owner_id` | Repository tenant filter | Indexed |
| --- | --- | --- | --- |
| `users` | — (is tenant root) | N/A | — |
| `accounts` | ✓ | `OwnedTableRepository` | ✓ |
| `types` | ✓ (nullable) | `TypesRepository` — global OR owned | ✓ |
| `accounts_indexer` | ✓ | `OwnedTableRepository` | ✓ |
| `assets_accounts` | ✓ | `OwnedTableRepository` | ✓ |
| `banking_asset_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `real_estate_asset_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `trading_asset_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `liability_accounts` | ✓ | `OwnedTableRepository` | ✓ |
| `bank_credit_liability_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `credit_card_liability_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `financed_asset_accounts` | ✓ | `OwnedTableRepository` | ✗ |
| `identified_transactions` | ✓ | `OwnedTableRepository` | ✗ |
| `transactions` | ✓ | `OwnedTableRepository` | ✓ |

### 6.2 Consistency enforcement

| Mechanism | Present? |
| --- | --- |
| DB trigger: child.owner_id = parent.owner_id | No |
| FK to `(id, owner_id)` composite | No |
| Service assignment on upsert | Yes — `OwnedTableRepository.upsert_records()` sets `owner_id` |
| DTO validation on mismatch | Yes — `upsert_record()` raises if DTO owner ≠ caller |

**Gap:** Direct SQL or bulk loads can insert mismatched `owner_id` values across the chain.

### 6.3 Tenancy strategy options (input for FR-02)

| Strategy | Description | v0 state |
| --- | --- | --- |
| **A — FK chain** | Drop redundant columns; filter via joins | Not implemented |
| **B — Denormalized** | Keep `owner_id`; app-layer enforcement | **Current default** |
| **C — RLS** | Postgres policies on `owner_id` | Not implemented |

### 6.4 Legacy migration risk

Migration `06b97dfcb5c7` adds `owner_id NOT NULL` **without backfill**. Pre-#26 PostgreSQL dumps fail `./deploy/alembic.sh upgrade` unless a default user is seeded manually (FR-14).

Handlers still accept `owner=None` on `load()` / `dump()` — records upserted without owner assignment rely on `BaseRepository.upsert_records()` injecting `kwargs.owner_id`, which is `None` if not provided.

---

## 7. Repository and handler query patterns

### 7.1 Repository tiers

| Repository | Base class | Tenant filtering |
| --- | --- | --- |
| `UsersRepository` | `BaseRepository` | None |
| `TypesRepository` | `BaseRepository` | Optional — `owner_id = X OR owner_id IS NULL` |
| All others | `OwnedTableRepository` | Required `owner` kwarg on all CRUD |

Source: [`access/base/repository.py`](../../modules/model/src/papita_txnsmodel/access/base/repository.py).

### 7.2 Common query patterns

| Use case | Pattern | Code path |
| --- | --- | --- |
| Get by ID | `dao.id == uuid` + owner filter | `get_record_by_id()` |
| Get by attributes | Non-null DTO fields → WHERE clauses | `get_records_from_attributes()` |
| List all for tenant | `Select(dao).where(owner_id == X)` | `OwnedTableRepository.get_records()` |
| List types for tenant | Global + owned merge | `TypesRepository.get_records(owner=...)` |
| List by type | `type_id == X` + owner | `TypedEntitiesService.get_records_by_type()` |
| Bulk ingest | `UpscribeFactory.get_upserter().upsert(df)` | `upsert_records()` |
| Soft delete | `active=false, deleted_at=now()` | `soft_delete_records()` |

### 7.3 Handler load patterns

| Handler | Service | Dependencies | Load behavior |
| --- | --- | --- | --- |
| `AccountsTableHandler` | `AccountsService` | none | build → upsert |
| `AssetAccountsTableHandler` | `AssetAccountsService` | none | build → upsert |
| `LiabilityAccountsTableHandler` | `LiabilityAccountsService` | none | build → upsert |
| `AccountsIndexerTableHandler` | `AccountsIndexerService` | 8 services | resolve all FKs via get_or_create |
| `FinancedAssetAccountsTableHandler` | `FinancedAssetAccountsService` | asset + bank credit | resolve both sides |
| `IdentifiedTransactionsTableHandler` | `IdentifiedTransactionsService` | TypesService | resolve type |
| `TransactionsHandler` | `TransactionsService` | AccountsService, IdentifiedTransactionsService | match accounts by name/tag/id (exact/fuzzy), filter invalid from/to pairs |

### 7.4 Transaction matching pipeline

`TransactionsHandler.load()` executes:

1. `_match_accounts()` — resolve `from_account_id` / `to_account_id` by ID, name, or tags
2. Filter rows where **exactly one** of from/to is non-null
3. `_match_identified_transactions()` — resolve template reference
4. `standardized_dataframe()` — coerce to DTO schema

Tenant scoping: matching queries call `accounts(owner=owner)` and `identified_transactions(owner=owner)` which pass through `OwnedTableRepository`.

### 7.5 Upsert behavior (PostgreSQL)

Bulk loads use `PostgreSQLUpserter` via `UpscribeFactory`. Conflict resolution defaults to `OnUpsertConflictDo.UPDATE` on handlers. `owner_id` injected in bulk path:

```python
# BaseRepository.upsert_records()
if "owner_id" not in mappings.columns and hasattr(dao, "owner_id"):
    mappings["owner_id"] = kwargs.get("owner_id")
```

If `owner=None`, bulk upsert writes **NULL owner_id** → NOT NULL constraint failure at DB layer.

---

## 8. Registrar / load pipeline impact summary

> **Note:** The `modules/registrar/` package is referenced in #28 but **not present** in the current workspace. Load handlers live in `modules/model/src/papita_txnsmodel/handlers/` and are the effective ingestion interface.

### 8.1 Handler registry

`HandlerFactory.load()` discovers handlers from `papita_txnsmodel.handlers` and registers by `labels()` + class name.

Registered handler labels (representative):

| Label | Handler |
| --- | --- |
| `accounts`, `accounts_table` | `AccountsTableHandler` |
| `assets`, `asset_accounts` | `AssetAccountsTableHandler` |
| `liabilities`, `liability_accounts` | `LiabilityAccountsTableHandler` |
| `accounts_indexer`, `indexer` | `AccountsIndexerTableHandler` |
| `financed_asset_accounts` | `FinancedAssetAccountsTableHandler` |
| `identified_transactions` | `IdentifiedTransactionsTableHandler` |
| `transactions`, `transactions_handler` | `TransactionsHandler` |

### 8.2 Typical load order (dependency-safe)

```
1. users          (tenant root — manual or API)
2. types          (classifications — may be global)
3. accounts       (shell rows)
4. assets_accounts / liability_accounts  (base financial rows)
5. *_asset_accounts / *_liability_accounts  (extensions)
6. accounts_indexer  (wires all FKs — MUST be after steps 3–5)
7. financed_asset_accounts  (cross-links credit ↔ asset)
8. identified_transactions  (templates)
9. transactions  (ledger — matches accounts/templates at load time)
```

**Breaking indexer before subtypes** → FK violations. **Breaking indexer entirely (v3)** → requires migration mapping + handler rewrite.

### 8.3 Impact of proposed v3 changes

| v3 change | Handler impact | Migration impact |
| --- | --- | --- |
| Remove `AccountsIndexer` | Rewrite `AccountsIndexerTableHandler`; simplify other account handlers | Backfill script: collapse indexer rows into new structure |
| Drop redundant `owner_id` | Remove `owner` param from subtype handlers OR derive from account | Column drops + consistency checks |
| Consolidate subtype tables | Merge handlers; update DTOs | Data migration per subtype |
| Types composite unique `(owner_id, name)` | Update `TypesDTO._normalize_model()` | Re-hash existing type IDs or remap FKs |
| Add `account_kind` enum | New validation in account load | Populate from indexer FK pattern |

### 8.4 Test coverage touchpoints

Existing tests under `modules/model/tests/` should be re-run after any schema change. Key paths:

- Indexer DTO validation (asset/liability XOR, extended type rules)
- `AccountsIndexerService.create()` classification check
- `TransactionsHandler` account matching (exact/fuzzy)
- `OwnedTableRepository` cross-tenant denial (may be incomplete — NFR-04)

---

## 9. Cross-reference: #28 pain points mapped to v0 evidence

| #28 pain point | v0 audit section | Evidence |
| --- | --- | --- |
| #1 Sparse FK matrix | §5 | 8 nullable FKs, no DB CHECK |
| #2 Redundant `owner_id` | §6 | 13 tables, no trigger sync |
| #6 Model doc drift | §3.9 | `LiabilityAccounts` docstring fields missing |
| #10 Types ID collision | §4.3.4 | `TypesDTO` hash excludes owner |
| #12 Indexer skips BaseSQLModel | §2.3, §3.4 | No soft delete on hub |
| #13 Legacy migration | §6.4 | NOT NULL without backfill |
| #16 FinancedAssetAccounts | §3.12, §4.2 | PK + share constraints |

---

## 10. v0 audit deliverable checklist (#30)

| Deliverable | Section |
| --- | --- |
| Table inventory: columns, PKs, FKs, indexes for all 14 tables | §3 |
| Normalization analysis (1NF / 2NF / 3NF) with concrete examples | §4 |
| `AccountsIndexer` complexity assessment (8 nullable FKs) | §5 |
| Redundant `owner_id` analysis (post PR #27) | §6 |
| Repository/handler query pattern notes | §7 |
| Registrar load pipeline impact summary | §8 |

---

## 11. Next steps (Track A continuation → #32)

1. **v1 target schema** — propose discriminator + single extension FK or consolidated accounts table.
2. **Tenancy decision (FR-02)** — choose FK-chain vs denormalized vs RLS; document in v3.
3. **Types identity (FR-15)** — include `owner_id` in hash or adopt composite unique.
4. **Intentional denormalizations** — document any retained `owner_id` on hot tables with rationale.
5. **Regenerate ER diagram** after v3 on Docker Postgres / Supabase (#34).

---

## References

- Parent issue: [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
- Sub-issues: [#30](https://github.com/Elmorralito/save-ma-money/issues/30) (this doc), [#32](https://github.com/Elmorralito/save-ma-money/issues/32) (v1–v3 schema)
- Models: [`modules/model/src/papita_txnsmodel/model/`](../../modules/model/src/papita_txnsmodel/model/)
- Migrations: [`modules/model/alembic/versions/`](../../modules/model/alembic/versions/)
- Handlers: [`modules/model/src/papita_txnsmodel/handlers/`](../../modules/model/src/papita_txnsmodel/handlers/)
- ER (stale): [`docs/postgres_papita_transactions.png`](../postgres_papita_transactions.png)
- Requirements: [`docs/issues/PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md)
