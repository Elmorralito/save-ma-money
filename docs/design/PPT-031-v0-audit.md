# PPT-031 v0: Data Model Audit and 3NF Gap Analysis

| Field                  | Value                                                                                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Issue**              | [#30 — Data model audit and 3NF gap analysis (v0)](https://github.com/Elmorralito/save-ma-money/issues/30)                 |
| **Parent**             | [#28 — refactor/PPT-031: Simplify data model and align API design](https://github.com/Elmorralito/save-ma-money/issues/28) |
| **Track**              | A — Step A1                                                                                                                |
| **Baseline**           | PR #27 (users + `owner_id`), PR #29 (API spec scaffold)                                                                    |
| **Schema**             | `papita_transactions` (PostgreSQL / Supabase)                                                                              |
| **Date**               | 2026-07-05                                                                                                                 |
| **Last expert review** | 2026-07-05 (10 iterations — see §13; stopped at quality plateau)                                                           |
| **Status**             | v0 baseline — pre-simplification                                                                                           |

---

## 1. Executive summary

This document captures the **current state** of the `papita_transactions` schema before PPT-031 simplification. It inventories all 14 SQLModel tables, analyzes normalization (1NF / 2NF / 3NF), assesses `AccountsIndexer` complexity, evaluates redundant `owner_id` columns introduced in PR #27, and documents how repositories, handlers, and the load pipeline interact with the schema today.

**Key findings:** (full register with evidence in [§14](#14-new-findings-register-expert-review-2026-07-05))

| Area                           | Finding                                                                                                     | Severity            |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------------- |
| **AccountsIndexer**            | 8 nullable FK columns with no DB constraint enforcing exactly one populated                                 | High                |
| **Redundant `owner_id`**       | Present on 13 tables; derivable via FK chains in most cases                                                 | Medium              |
| **3NF violations**             | Transitive dependencies via duplicated financial columns across base + subtype tables; denormalized tenancy | Medium–High         |
| **Types identity**             | Deterministic UUID ignores `owner_id`; `name` is globally unique                                            | High (multi-tenant) |
| **AccountsIndexer audit gap**  | Does not extend `BaseSQLModel` — no soft delete or timestamps                                               | Medium              |
| **Load pipeline**              | Deep dependency chains through indexer handler; `owner=None` still accepted                                 | Medium              |
| **Ledger semantics**           | Single-sided entries only at ingest; **transfers rejected** by handler                                      | High (domain)       |
| **Missing primitives**         | No `currency`, stored `balance`, or double-entry journal lines                                              | High (API gap)      |
| **Indexer DTO bug**            | `_validate_linked_accounts()` rejects any populated extended subtype                                        | Critical (runtime)  |
| **DTO default contradictions** | `total_paid=0` with `gt=0`; `financing_share=0.0` with `gt=0` — new rows fail validation                    | Critical (runtime)  |
| **Types write asymmetry**      | Read merges global+owned; write uses `BaseRepository` without owner enforcement                             | High (security)     |
| **Report index gaps**          | No FK indexes on `from_account_id`/`to_account_id`; no `(owner_id, transaction_ts)` composite               | Medium (perf)       |

The v0 schema is **functional for single-tenant cash-flow ingestion** (income/expense against named accounts) but is **not** a general ledger, multi-currency portfolio system, or clean multi-tenant product schema. Structural debt blocks API CRUD (#25) and tenant isolation (#24) without redesign (#32).

### 1.1 Domain context (personal finance vs accounting)

| Concept                | v0 representation                                                                        | Typical PF/ accounting expectation                          |
| ---------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Chart of accounts**  | `accounts` shell + `types.classification` (ASSETS / LIABILITIES / TRANSACTIONS)          | COA hierarchy with account codes                            |
| **Account balance**    | Not stored; implied by `assets_accounts.last_value` / `liability_accounts.present_value` | Running balance or derived from ledger                      |
| **Categories**         | `types` where `classification = TRANSACTIONS`                                            | income/expense tags; API spec uses `/categories`            |
| **Budget / recurring** | `identified_transactions` (planned value, day-of-month)                                  | budget lines or scheduled transactions                      |
| **Posted activity**    | `transactions` (single `value`, one account side)                                        | transfer pair or double-entry lines                         |
| **Multi-currency**     | Absent                                                                                   | `currency` on account and transaction (API spec expects it) |

**Positioning:** v0 is closer to a **typed account register + cash-flow log** than to double-entry bookkeeping. That is valid for personal finance if documented; it conflicts with API fields (`balance`, `currency`, `transaction_type`) defined in PR #29.

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

| Pattern                          | Tables                                                         |
| -------------------------------- | -------------------------------------------------------------- |
| Extends `BaseSQLModel`           | 13 tables — `active`, `deleted_at`, `created_at`, `updated_at` |
| Raw `SQLModel` (no audit fields) | `accounts_indexer` only                                        |

Source: [`modules/model/src/papita_txnsmodel/model/base.py`](../../modules/model/src/papita_txnsmodel/model/base.py), [`indexers.py`](../../modules/model/src/papita_txnsmodel/model/indexers.py).

---

## 3. Table inventory

All tables live in schema **`papita_transactions`**. Index names follow Alembic convention `ix_papita_transactions_<table>_<column>`.

### 3.1 `users`

| Column       | Type      | Nullable | Notes                             |
| ------------ | --------- | -------- | --------------------------------- |
| `id`         | UUID      | NO       | PK                                |
| `username`   | VARCHAR   | NO       | unique                            |
| `email`      | VARCHAR   | NO       | unique                            |
| `password`   | VARCHAR   | NO       | Argon2 hash at DTO serialize time |
| `active`     | BOOLEAN   | NO       | default `true`                    |
| `deleted_at` | TIMESTAMP | YES      | soft delete                       |
| `created_at` | TIMESTAMP | NO       |                                   |
| `updated_at` | TIMESTAMP | NO       |                                   |

**PK:** `id`

**FKs:** none (tenant root)

**Indexes:** `id`, `username` (unique), `email` (unique)

**Model:** [`model/users.py`](../../modules/model/src/papita_txnsmodel/model/users.py)

---

### 3.2 `accounts`

| Column                                             | Type      | Nullable | Notes                          |
| -------------------------------------------------- | --------- | -------- | ------------------------------ |
| `id`                                               | UUID      | NO       | PK, auto-generated             |
| `name`                                             | VARCHAR   | NO       |                                |
| `description`                                      | TEXT      | NO       |                                |
| `tags`                                             | VARCHAR[] | NO       | min 1, unique items (Pydantic) |
| `start_ts`                                         | TIMESTAMP | NO       | indexed                        |
| `end_ts`                                           | TIMESTAMP | YES      | indexed                        |
| `owner_id`                                         | UUID      | NO       | FK → `users.id`                |
| `active`, `deleted_at`, `created_at`, `updated_at` | —         | —        | BaseSQLModel                   |

**PK:** `id`

**FKs:** `owner_id` → `users.id`

**Indexes:** `name`, `start_ts`, `end_ts`, `owner_id`

---

### 3.3 `types`

| Column                                             | Type      | Nullable | Notes                                                       |
| -------------------------------------------------- | --------- | -------- | ----------------------------------------------------------- |
| `id`                                               | UUID      | NO       | PK; deterministic uuid5 from `name + classification` in DTO |
| `classification`                                   | ENUM      | NO       | `ASSETS`, `LIABILITIES`, `TRANSACTIONS`                     |
| `name`                                             | VARCHAR   | NO       | **globally unique**                                         |
| `tags`                                             | VARCHAR[] | NO       |                                                             |
| `description`                                      | TEXT      | NO       |                                                             |
| `owner_id`                                         | UUID      | YES      | FK → `users.id`; NULL = global type                         |
| `active`, `deleted_at`, `created_at`, `updated_at` | —         | —        | BaseSQLModel                                                |

**PK:** `id`

**FKs:** `owner_id` → `users.id` (nullable since migration `255bb7382571`)

**Indexes:** `classification`, `name` (unique), `owner_id`

---

### 3.4 `accounts_indexer`

Central polymorphic hub — **does not extend `BaseSQLModel`**.

| Column                             | Type | Nullable | Notes                                    |
| ---------------------------------- | ---- | -------- | ---------------------------------------- |
| `account_id`                       | UUID | NO       | PK; FK → `accounts.id`                   |
| `type_id`                          | UUID | NO       | FK → `types.id`                          |
| `owner_id`                         | UUID | NO       | FK → `users.id` (PR #27)                 |
| `asset_account_id`                 | UUID | YES      | FK → `assets_accounts.id`                |
| `liability_account_id`             | UUID | YES      | FK → `liability_accounts.id`             |
| `banking_asset_account_id`         | UUID | YES      | FK → `banking_asset_accounts.id`         |
| `real_estate_asset_account_id`     | UUID | YES      | FK → `real_estate_asset_accounts.id`     |
| `trading_asset_account_id`         | UUID | YES      | FK → `trading_asset_accounts.id`         |
| `bank_credit_liability_account_id` | UUID | YES      | FK → `bank_credit_liability_accounts.id` |
| `credit_card_liability_account_id` | UUID | YES      | FK → `credit_card_liability_accounts.id` |

**PK:** `account_id` (1:1 with `accounts`)

**FKs:** 9 outbound FKs (account, type, owner, 6 subtype columns)

**Indexes:** `type_id`, `owner_id`

**Missing vs other tables:** no `active`, `deleted_at`, `created_at`, `updated_at`

---

### 3.5 `assets_accounts`

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `months_per_period`                                | SMALLINT      | NO       | default 1, > 0  |
| `initial_value`                                    | DECIMAL(22,8) | YES      | > 0             |
| `last_value`                                       | DECIMAL(22,8) | YES      | > 0             |
| `monthly_interest_rate`                            | DECIMAL(10,4) | YES      | > 0             |
| `yearly_interest_rate`                             | DECIMAL(10,4) | YES      | > 0             |
| `roi`                                              | DECIMAL(10,4) | YES      | > 0             |
| `periodical_earnings`                              | DECIMAL(22,8) | YES      | > 0             |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.asset_account_id`, `financed_asset_accounts.asset_account_id`

**Indexes:** `owner_id`

---

### 3.6 `banking_asset_accounts`

| Column                                             | Type    | Nullable | Notes                                |
| -------------------------------------------------- | ------- | -------- | ------------------------------------ |
| `id`                                               | UUID    | NO       | PK (extends `ExtendedAssetAccounts`) |
| `entity`                                           | VARCHAR | NO       | bank name                            |
| `account_number`                                   | VARCHAR | YES      |                                      |
| `owner_id`                                         | UUID    | NO       | FK → `users.id`                      |
| `active`, `deleted_at`, `created_at`, `updated_at` | —       | —        | BaseSQLModel                         |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.banking_asset_account_id`

**Indexes:** `entity`, `account_number`

---

### 3.7 `real_estate_asset_accounts`

| Column                                             | Type          | Nullable | Notes                               |
| -------------------------------------------------- | ------------- | -------- | ----------------------------------- |
| `id`                                               | UUID          | NO       | PK                                  |
| `address`, `city`, `country`                       | VARCHAR       | NO       |                                     |
| `total_area`, `built_area`                         | DECIMAL(12,4) | NO       | > 0                                 |
| `area_unit`                                        | ENUM          | NO       | `SQ_MT`, `SQ_FT`, `AC`, `HA`, `BLK` |
| `ownership`                                        | ENUM          | NO       | `FULL`, `PARTIAL`                   |
| `participation`                                    | DECIMAL(4,4)  | NO       | 0–1, default 1.0                    |
| `owner_id`                                         | UUID          | NO       | FK → `users.id`                     |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel                        |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.real_estate_asset_account_id`

**Indexes:** none beyond PK

---

### 3.8 `trading_asset_accounts`

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `buy_value`                                        | DECIMAL(22,8) | NO       | > 0             |
| `last_value`                                       | DECIMAL(22,8) | YES      | > 0             |
| `units`                                            | SMALLINT      | NO       | default 1, > 0  |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.trading_asset_account_id`

**Indexes:** none beyond PK

**Note:** `last_value` duplicated conceptually with `assets_accounts.last_value` when both rows exist for the same logical account.

---

### 3.9 `liability_accounts`

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `months_per_period`                                | SMALLINT      | YES      | default 1       |
| `initial_value`, `present_value`                   | DECIMAL(22,8) | NO       | > 0             |
| `monthly_interest_rate`, `yearly_interest_rate`    | DECIMAL(10,4) | YES      | > 0             |
| `payment`, `total_paid`                            | DECIMAL(22,8) | NO       | > 0             |
| `overall_periods`, `periods_paid`                  | SMALLINT      | NO       | > 0             |
| `closing_day`                                      | SMALLINT      | NO       | 1–28            |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.liability_account_id`

**Indexes:** `owner_id`

**Doc drift:** model docstring references `account_id` / `type_id` fields that **do not exist** on the DAO.

---

### 3.10 `bank_credit_liability_accounts`

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `paid`                                             | BOOLEAN       | NO       | default false   |
| `insurance_payment`, `extras_payment`              | DECIMAL(22,8) | NO       |                 |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.bank_credit_liability_account_id`, `financed_asset_accounts.bank_credit_liability_account_id`

**Indexes:** none beyond PK

---

### 3.11 `credit_card_liability_accounts`

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `credit_limit`                                     | DECIMAL(22,8) | NO       |                 |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `owner_id` → `users.id`; referenced by `accounts_indexer.credit_card_liability_account_id`

**Indexes:** none beyond PK

---

### 3.12 `financed_asset_accounts`

Join table linking bank credit liabilities to assets.

| Column                                             | Type         | Nullable | Notes                                        |
| -------------------------------------------------- | ------------ | -------- | -------------------------------------------- |
| `bank_credit_liability_account_id`                 | UUID         | NO       | PK; FK → `bank_credit_liability_accounts.id` |
| `asset_account_id`                                 | UUID         | NO       | FK → `assets_accounts.id`                    |
| `financing_share`                                  | DECIMAL(4,4) | NO       | 0–1, default 1.0                             |
| `owner_id`                                         | UUID         | NO       | FK → `users.id`                              |
| `active`, `deleted_at`, `created_at`, `updated_at` | —            | —        | BaseSQLModel                                 |

**PK:** `bank_credit_liability_account_id` only — **one credit → one asset**; one asset may have many credits only if PK design changes.

**FKs:** both account FKs + `owner_id` → `users.id`

**Indexes:** none beyond PK

**Integrity gaps:** no CHECK that asset, liability, and join `owner_id` values match; no constraint that financing shares sum to 1.0 per asset.

---

### 3.13 `identified_transactions`

Transaction templates / recurring plans.

| Column                                             | Type          | Nullable | Notes           |
| -------------------------------------------------- | ------------- | -------- | --------------- |
| `id`                                               | UUID          | NO       | PK              |
| `type_id`                                          | UUID          | NO       | FK → `types.id` |
| `name`                                             | VARCHAR       | NO       | indexed         |
| `tags`                                             | VARCHAR[]     | NO       |                 |
| `description`                                      | VARCHAR       | NO       |                 |
| `planned_value`                                    | DECIMAL(22,8) | NO       | > 0             |
| `planned_transaction_day`                          | SMALLINT      | NO       | 1–28            |
| `owner_id`                                         | UUID          | NO       | FK → `users.id` |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel    |

**PK:** `id`

**FKs:** `type_id` → `types.id`, `owner_id` → `users.id`

**Indexes:** `name`

---

### 3.14 `transactions`

Posted ledger entries.

| Column                                             | Type          | Nullable | Notes                             |
| -------------------------------------------------- | ------------- | -------- | --------------------------------- |
| `id`                                               | UUID          | NO       | PK                                |
| `identified_transaction_id`                        | UUID          | YES      | FK → `identified_transactions.id` |
| `from_account_id`                                  | UUID          | YES      | FK → `accounts.id`                |
| `to_account_id`                                    | UUID          | YES      | FK → `accounts.id`                |
| `transaction_ts`                                   | TIMESTAMP     | NO       | indexed                           |
| `value`                                            | DECIMAL(22,8) | NO       | > 0                               |
| `owner_id`                                         | UUID          | NO       | FK → `users.id`                   |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel                      |

**PK:** `id`

**FKs:** three optional/required FKs + `owner_id` → `users.id`

**Indexes:** `transaction_ts`, `owner_id`

**Missing indexes (NF-18):** No index on `from_account_id`, `to_account_id`, or `identified_transaction_id` — balance rollups and template joins require sequential scans at scale. No composite `(owner_id, transaction_ts)` for tenant-scoped time-series (#28 Track F / FR-12).

**Business rule (handler-enforced):** exactly one of `from_account_id` or `to_account_id` must be non-null (income vs expense).

**Transfer gap (NF-01):** `TransactionsHandler._match_accounts()` **drops rows where both** `from_account_id` and `to_account_id` are populated. Inter-account transfers (checking → savings) cannot be ingested through the current pipeline.

**Orphan row gap (NF-02):** The same filter drops rows where **neither** account FK is set after matching — unallocated / external-only rows without a resolved account are silently removed.

**Pair integrity (NF-03):** Modeling a transfer requires two single-sided rows manually; the schema has no `transfer_group_id`, paired FK, or double-entry lines to keep them in sync.

Filter logic (source):

```361:366:modules/model/src/papita_txnsmodel/handlers/transactions.py
        return data_.loc[
            ~(
                (pd.isna(data_[from_account_id_column]) & pd.isna(data_[to_account_id_column]))
                | (~pd.isna(data_[from_account_id_column]) & ~pd.isna(data_[to_account_id_column]))
            )
        ]
```

**Sign convention (NF-10):** `value` is always positive (`gt=0`). Direction is encoded only by which side (from = outflow, to = inflow) is set — implicit, not enumerated in the model.

---

## 4. Normalization analysis

### 4.1 First normal form (1NF)

| Table         | 1NF status | Notes                                                              |
| ------------- | ---------- | ------------------------------------------------------------------ |
| All 14 tables | **Pass**   | Atomic scalar columns; `tags` stored as PostgreSQL `ARRAY(String)` |

**1NF consideration — `tags` arrays:**

- Stored as multi-value arrays on `accounts`, `types`, `identified_transactions`.
- Acceptable as 1NF if treated as atomic multi-value attributes, but **not query-friendly** for tag-based filters without `unnest()` or GIN indexes.
- v3 decision needed: keep arrays vs junction table `entity_tags(entity_type, entity_id, tag)`.

**Example:** Two accounts tagged `"primary"` require `WHERE 'primary' = ANY(tags)` — no normalized tag index today.

---

### 4.2 Second normal form (2NF)

2NF applies when a non-key column depends on **part of** a composite primary key.

| Table                        | 2NF status | Analysis                                                                                                                                                                                              |
| ---------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Single-column PK tables (12) | **Pass**   | No partial key dependencies                                                                                                                                                                           |
| `accounts_indexer`           | **Pass**   | PK is `account_id` only                                                                                                                                                                               |
| `financed_asset_accounts`    | **Review** | PK is only `bank_credit_liability_account_id`. `asset_account_id` and `financing_share` depend on the full relationship `(credit_id, asset_id)`. If many-to-many is intended, PK should be composite. |

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

| Table                            | `owner_id` derivable via                                   | Redundant?                  |
| -------------------------------- | ---------------------------------------------------------- | --------------------------- |
| `accounts_indexer`               | `account_id` → `accounts.owner_id`                         | Yes                         |
| `assets_accounts`                | `accounts_indexer.account_id` → `accounts.owner_id`        | Yes                         |
| `banking_asset_accounts`         | same chain via indexer                                     | Yes                         |
| `real_estate_asset_accounts`     | same                                                       | Yes                         |
| `trading_asset_accounts`         | same                                                       | Yes                         |
| `liability_accounts`             | same                                                       | Yes                         |
| `bank_credit_liability_accounts` | same                                                       | Yes                         |
| `credit_card_liability_accounts` | same                                                       | Yes                         |
| `financed_asset_accounts`        | either FK side → indexer → accounts                        | Yes                         |
| `transactions`                   | `from_account_id` or `to_account_id` → `accounts.owner_id` | Mostly yes\*                |
| `identified_transactions`        | `type_id` → `types.owner_id` (when not global)             | Partial\*\*                 |
| `types`                          | self — tenant root for taxonomy                            | No (when used as scope key) |
| `accounts`                       | self                                                       | No                          |

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

| Base column (`assets_accounts`)        | Also on subtype                     | Transitive dependency                                                   |
| -------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------- |
| `last_value`                           | `trading_asset_accounts.last_value` | Subtype value may diverge from base                                     |
| `initial_value`, interest rates, `roi` | —                                   | Base holds generic attrs; subtype adds specifics without FK to base row |

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

| Table                            | 1NF | 2NF | 3NF | Primary issue                                     |
| -------------------------------- | --- | --- | --- | ------------------------------------------------- |
| `users`                          | ✓   | ✓   | ✓   | —                                                 |
| `accounts`                       | ✓   | ✓   | ✓   | —                                                 |
| `types`                          | ✓   | ✓   | △   | Global unique `name` + nullable `owner_id`        |
| `accounts_indexer`               | ✓   | ✓   | ✗   | Redundant `owner_id`, `type_id`; sparse FK matrix |
| `assets_accounts`                | ✓   | ✓   | ✗   | Redundant `owner_id`; overlaps with subtypes      |
| `banking_asset_accounts`         | ✓   | ✓   | ✗   | Redundant `owner_id`                              |
| `real_estate_asset_accounts`     | ✓   | ✓   | ✗   | Redundant `owner_id`                              |
| `trading_asset_accounts`         | ✓   | ✓   | ✗   | Redundant `owner_id`; `last_value` overlap        |
| `liability_accounts`             | ✓   | ✓   | ✗   | Redundant `owner_id`                              |
| `bank_credit_liability_accounts` | ✓   | ✓   | ✗   | Redundant `owner_id`                              |
| `credit_card_liability_accounts` | ✓   | ✓   | ✗   | Redundant `owner_id`                              |
| `financed_asset_accounts`        | ✓   | △   | ✗   | PK design; redundant `owner_id`                   |
| `identified_transactions`        | ✓   | ✓   | △   | `owner_id` partially derivable                    |
| `transactions`                   | ✓   | ✓   | ✗   | Redundant `owner_id`                              |

**Legend:** ✓ compliant, ✗ violation, △ partial / context-dependent

### 4.5 Domain and financial modeling gaps (beyond classical NF)

Normalization to 3NF does not by itself produce a **correct personal-finance domain model**. Gaps that affect #25 / #33 regardless of NF:

| Gap                                   | v0 state                                                         | Risk                                                                           |
| ------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **No currency**                       | All amounts unitless DECIMAL                                     | Cannot sum across accounts; FX impossible                                      |
| **No stored or derived balance view** | Snapshot fields on asset/liability rows drift from ledger        | API `balance` / `initial_balance` are phantom columns                          |
| **Single-sided ledger**               | One account FK per transaction                                   | Transfers, CC payments, loan disbursements awkward                             |
| **Types vs categories**               | Flat `types`; no `parent_id`, no income/expense enum             | API category hierarchy unsupported                                             |
| **Interest rate duplication**         | Monthly + yearly on assets and liabilities, no consistency check | APR vs nominal ambiguity; redundant storage                                    |
| **Real estate valuation**             | `participation` × area on subtype; `last_value` on base asset    | NAV for partial ownership unclear                                              |
| **Credit card model**                 | `credit_limit` only; no statement cycle, APR, minimum payment    | Liability lifecycle incomplete                                                 |
| **Mortgage link**                     | `financed_asset_accounts` join                                   | Correct direction for asset–liability pairing; PK limits many-credit scenarios |

**Balance authority (expert rule):** For v3, pick **one** source of truth:

1. **Ledger-derived** — balance = Σ(inflows) − Σ(outflows) per account (preferred for PF apps), or
2. **Snapshot** — `last_value` / `present_value` updated by batch jobs (current implicit model).

v0 mixes both without reconciliation — a **domain integrity** issue, not merely 3NF.

### 4.6 Subtype column overlap (consolidation input for #32)

| Shared financial concept | `assets_accounts`              | `liability_accounts`             | Subtype-only columns                 |
| ------------------------ | ------------------------------ | -------------------------------- | ------------------------------------ |
| Periodicity              | `months_per_period`            | `months_per_period`              | —                                    |
| Principal / value        | `initial_value`, `last_value`  | `initial_value`, `present_value` | trading: `buy_value`, `units`        |
| Interest                 | `monthly_*`, `yearly_*`, `roi` | `monthly_*`, `yearly_*`          | —                                    |
| Earnings / payments      | `periodical_earnings`          | `payment`, `total_paid`, periods | bank credit: insurance/extras        |
| Identity / location      | —                              | —                                | banking: `entity`; RE: address, area |

**Overlap estimate:** ~70% of numeric columns on base asset/liability rows are shared semantics. v3 consolidation into `accounts` + optional 1:1 extension (or JSONB exception documented per FR-04) is financially justified — fewer places for `present_value` and `last_value` to diverge.

---

## 5. `AccountsIndexer` complexity assessment

### 5.1 Sparse FK matrix

The indexer holds **8 nullable FK columns** representing subtype rows. Design intent: exactly **one base** FK (`asset_account_id` XOR `liability_account_id`) and **at most one extended** FK populated.

| FK column                          | Target table                     | Layer               |
| ---------------------------------- | -------------------------------- | ------------------- |
| `asset_account_id`                 | `assets_accounts`                | Base asset          |
| `liability_account_id`             | `liability_accounts`             | Base liability      |
| `banking_asset_account_id`         | `banking_asset_accounts`         | Asset extension     |
| `real_estate_asset_account_id`     | `real_estate_asset_accounts`     | Asset extension     |
| `trading_asset_account_id`         | `trading_asset_accounts`         | Asset extension     |
| `bank_credit_liability_account_id` | `bank_credit_liability_accounts` | Liability extension |
| `credit_card_liability_account_id` | `credit_card_liability_accounts` | Liability extension |

**Database enforcement:** none. PostgreSQL accepts rows with 0, 2, or all 8 FKs populated.

### 5.2 Application-layer enforcement

| Layer       | Enforcement mechanism                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------ |
| **DTO**     | `AccountsIndexerDTO._validate_accounts()` — XOR asset/liability                                        |
| **DTO**     | `_validate_extended_accounts()` — at most one extended type                                            |
| **DTO**     | `_validate_linked_accounts()` — **bug:** extended subtype fields always fail when populated (see §5.6) |
| **Service** | `AccountsIndexerService.create()` — type classification must match asset vs liability                  |
| **Service** | `TypedLinkedEntitiesServiceMixin` — cascades `get_or_create` across 7 linked services                  |

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

| Dimension             | Rating (1–5) | Notes                                                    |
| --------------------- | ------------ | -------------------------------------------------------- |
| Schema comprehension  | 5            | New developers must learn polymorphic hub pattern        |
| Write-path complexity | 5            | 8-dependency handler + DTO validators                    |
| Read-path complexity  | 4            | Multi-join or service-side linked DTO hydration          |
| DB integrity          | 1            | No CHECK constraints on FK matrix                        |
| Migration risk        | 5            | Central hub — any v3 change touches all account subtypes |
| Test surface          | 4            | Combinatorial subtype × validation paths                 |

**Recommendation (for #32):** Replace with discriminator + single extension FK, or consolidated `accounts` row with `account_kind` enum (per FR-03, FR-04).

### 5.6 Critical: `AccountsIndexerDTO._validate_linked_accounts()` defect

Source: [`access/indexers/dto.py`](../../modules/model/src/papita_txnsmodel/access/indexers/dto.py) lines 187–201.

The validator builds `extended_account_fields` with:

```python
if extended_account_type in get_args(info.annotation)
   or ExtendedLiabilityAccountsDTO in get_args(info.annotation)  # always includes liability extended fields
```

Then raises if **any** extended field is non-null. Effect:

- A valid banking asset indexer row (`asset_account` + `banking_asset_account` set) **always raises** `ValueError`.
- The asset/liability branch labels are also **swapped** (`case None, _` assigns `ExtendedAssetAccountsDTO` when liability is the base).

**Impact:** Extended subtypes (banking, real estate, trading, credit card, bank credit) may be **unloadable via DTO validation** unless loaders bypass validation or populate only base asset/liability FKs. This explains hub-only rows in the wild and is a **blocker** for correct subtype ingestion until fixed or indexer is removed in v3.

---

## 6. Redundant `owner_id` analysis (post PR #27)

PR #27 ([`06b97dfcb5c7`](../../modules/model/alembic/versions/2026_01_28_1921-06b97dfcb5c7_adding_user_table_and_owner_columns.py)) added `owner_id NOT NULL` to 12 child tables plus created `users`. Migration `255bb7382571` later made `types.owner_id` nullable for global types.

### 6.1 Coverage matrix

| Table                            | Has `owner_id`     | Repository tenant filter            | Indexed |
| -------------------------------- | ------------------ | ----------------------------------- | ------- |
| `users`                          | — (is tenant root) | N/A                                 | —       |
| `accounts`                       | ✓                  | `OwnedTableRepository`              | ✓       |
| `types`                          | ✓ (nullable)       | `TypesRepository` — global OR owned | ✓       |
| `accounts_indexer`               | ✓                  | `OwnedTableRepository`              | ✓       |
| `assets_accounts`                | ✓                  | `OwnedTableRepository`              | ✓       |
| `banking_asset_accounts`         | ✓                  | `OwnedTableRepository`              | ✗       |
| `real_estate_asset_accounts`     | ✓                  | `OwnedTableRepository`              | ✗       |
| `trading_asset_accounts`         | ✓                  | `OwnedTableRepository`              | ✗       |
| `liability_accounts`             | ✓                  | `OwnedTableRepository`              | ✓       |
| `bank_credit_liability_accounts` | ✓                  | `OwnedTableRepository`              | ✗       |
| `credit_card_liability_accounts` | ✓                  | `OwnedTableRepository`              | ✗       |
| `financed_asset_accounts`        | ✓                  | `OwnedTableRepository`              | ✗       |
| `identified_transactions`        | ✓                  | `OwnedTableRepository`              | ✗       |
| `transactions`                   | ✓                  | `OwnedTableRepository`              | ✓       |

### 6.2 Consistency enforcement

| Mechanism                                    | Present?                                                      |
| -------------------------------------------- | ------------------------------------------------------------- |
| DB trigger: child.owner_id = parent.owner_id | No                                                            |
| FK to `(id, owner_id)` composite             | No                                                            |
| Service assignment on upsert                 | Yes — `OwnedTableRepository.upsert_records()` sets `owner_id` |
| DTO validation on mismatch                   | Yes — `upsert_record()` raises if DTO owner ≠ caller          |

**Gap:** Direct SQL or bulk loads can insert mismatched `owner_id` values across the chain.

### 6.3 Tenancy strategy options (input for FR-02)

| Strategy             | Description                              | v0 state            |
| -------------------- | ---------------------------------------- | ------------------- |
| **A — FK chain**     | Drop redundant columns; filter via joins | Not implemented     |
| **B — Denormalized** | Keep `owner_id`; app-layer enforcement   | **Current default** |
| **C — RLS**          | Postgres policies on `owner_id`          | Not implemented     |

### 6.4 Legacy migration risk

Migration `06b97dfcb5c7` adds `owner_id NOT NULL` **without backfill**. Pre-#26 PostgreSQL dumps fail `./deploy/alembic.sh upgrade` unless a default user is seeded manually (FR-14).

Handlers still accept `owner=None` on `load()` / `dump()` — records upserted without owner assignment rely on `BaseRepository.upsert_records()` injecting `kwargs.owner_id`, which is `None` if not provided.

---

## 7. Repository and handler query patterns

### 7.1 Repository tiers

| Repository        | Base class             | Tenant filtering                              |
| ----------------- | ---------------------- | --------------------------------------------- |
| `UsersRepository` | `BaseRepository`       | None                                          |
| `TypesRepository` | `BaseRepository`       | Optional — `owner_id = X OR owner_id IS NULL` |
| All others        | `OwnedTableRepository` | Required `owner` kwarg on all CRUD            |

Source: [`access/base/repository.py`](../../modules/model/src/papita_txnsmodel/access/base/repository.py).

### 7.2 Common query patterns

| Use case              | Pattern                                     | Code path                                    |
| --------------------- | ------------------------------------------- | -------------------------------------------- |
| Get by ID             | `dao.id == uuid` + owner filter             | `get_record_by_id()`                         |
| Get by attributes     | Non-null DTO fields → WHERE clauses         | `get_records_from_attributes()`              |
| List all for tenant   | `Select(dao).where(owner_id == X)`          | `OwnedTableRepository.get_records()`         |
| List types for tenant | Global + owned merge                        | `TypesRepository.get_records(owner=...)`     |
| List by type          | `type_id == X` + owner                      | `TypedEntitiesService.get_records_by_type()` |
| Bulk ingest           | `UpscribeFactory.get_upserter().upsert(df)` | `upsert_records()`                           |
| Soft delete           | `active=false, deleted_at=now()`            | `soft_delete_records()`                      |

### 7.3 Handler load patterns

| Handler                              | Service                         | Dependencies                                   | Load behavior                                                             |
| ------------------------------------ | ------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------- |
| `AccountsTableHandler`               | `AccountsService`               | none                                           | build → upsert                                                            |
| `AssetAccountsTableHandler`          | `AssetAccountsService`          | none                                           | build → upsert                                                            |
| `LiabilityAccountsTableHandler`      | `LiabilityAccountsService`      | none                                           | build → upsert                                                            |
| `AccountsIndexerTableHandler`        | `AccountsIndexerService`        | 8 services                                     | resolve all FKs via get_or_create                                         |
| `FinancedAssetAccountsTableHandler`  | `FinancedAssetAccountsService`  | asset + bank credit                            | resolve both sides                                                        |
| `IdentifiedTransactionsTableHandler` | `IdentifiedTransactionsService` | TypesService                                   | resolve type                                                              |
| `TransactionsHandler`                | `TransactionsService`           | AccountsService, IdentifiedTransactionsService | match accounts by name/tag/id (exact/fuzzy), filter invalid from/to pairs |

### 7.4 Transaction matching pipeline

`TransactionsHandler.load()` executes:

1. `_match_accounts()` — resolve `from_account_id` / `to_account_id` by ID, name, or tags
2. Filter rows where **exactly one** of from/to is non-null
3. `_match_identified_transactions()` — resolve template reference
4. `standardized_dataframe()` — coerce to DTO schema

Tenant scoping: matching queries call `accounts(owner=owner)` and `identified_transactions(owner=owner)` which pass through `OwnedTableRepository`.

### 7.5 Upsert behavior (PostgreSQL)

Bulk loads use `PostgreSQLUpserter` via `UpserterFactory`. Conflict resolution defaults to `OnUpsertConflictDo.UPDATE` on handlers. `owner_id` injected in bulk path:

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

| Label                                  | Handler                              |
| -------------------------------------- | ------------------------------------ |
| `accounts`, `accounts_table`           | `AccountsTableHandler`               |
| `assets`, `asset_accounts`             | `AssetAccountsTableHandler`          |
| `liabilities`, `liability_accounts`    | `LiabilityAccountsTableHandler`      |
| `accounts_indexer`, `indexer`          | `AccountsIndexerTableHandler`        |
| `financed_asset_accounts`              | `FinancedAssetAccountsTableHandler`  |
| `identified_transactions`              | `IdentifiedTransactionsTableHandler` |
| `transactions`, `transactions_handler` | `TransactionsHandler`                |

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

| v3 change                                 | Handler impact                                                         | Migration impact                                          |
| ----------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------- |
| Remove `AccountsIndexer`                  | Rewrite `AccountsIndexerTableHandler`; simplify other account handlers | Backfill script: collapse indexer rows into new structure |
| Drop redundant `owner_id`                 | Remove `owner` param from subtype handlers OR derive from account      | Column drops + consistency checks                         |
| Consolidate subtype tables                | Merge handlers; update DTOs                                            | Data migration per subtype                                |
| Types composite unique `(owner_id, name)` | Update `TypesDTO._normalize_model()`                                   | Re-hash existing type IDs or remap FKs                    |
| Add `account_kind` enum                   | New validation in account load                                         | Populate from indexer FK pattern                          |

### 8.4 Test coverage touchpoints

Existing tests under `modules/model/tests/` should be re-run after any schema change. Key paths:

- Indexer DTO validation (asset/liability XOR, extended type rules)
- `AccountsIndexerService.create()` classification check
- `TransactionsHandler` account matching (exact/fuzzy)
- `OwnedTableRepository` cross-tenant denial (may be incomplete — NFR-04)

---

## 9. Cross-reference: #28 pain points mapped to v0 evidence

| #28 pain point                 | v0 audit section   | Evidence                                       |
| ------------------------------ | ------------------ | ---------------------------------------------- |
| #1 Sparse FK matrix            | §5                 | 8 nullable FKs, no DB CHECK                    |
| #2 Redundant `owner_id`        | §6                 | 13 tables, no trigger sync                     |
| #6 Model doc drift             | §3.9               | `LiabilityAccounts` docstring fields missing   |
| #10 Types ID collision         | §4.3.4             | `TypesDTO` hash excludes owner                 |
| #12 Indexer skips BaseSQLModel | §2.3, §3.4         | No soft delete on hub                          |
| #13 Legacy migration           | §6.4               | NOT NULL without backfill                      |
| #16 FinancedAssetAccounts      | §3.12, §4.2        | PK + share constraints                         |
| Transfer ingestion             | §3.14, NF-01–NF-03 | Handler rejects both from/to; no pair link     |
| API phantom fields             | §1.1, §4.5, NF-09  | No currency/balance in model                   |
| Indexer DTO defect             | §5.6, NF-04        | Extended subtype validation broken             |
| DTO default defects            | §14 NF-13, NF-14   | Liability / financed share impossible defaults |
| Types write asymmetry          | §14 NF-15          | No owner on type upsert                        |
| Report query prerequisites     | §15                | Balance/spending SQL + index gaps              |
| Expert review register         | §14                | NF-01 through NF-20                            |

---

## 10. v0 audit deliverable checklist (#30)

| Deliverable                                                     | Section |
| --------------------------------------------------------------- | ------- |
| Table inventory: columns, PKs, FKs, indexes for all 14 tables   | §3      |
| Normalization analysis (1NF / 2NF / 3NF) with concrete examples | §4      |
| `AccountsIndexer` complexity assessment (8 nullable FKs)        | §5      |
| Redundant `owner_id` analysis (post PR #27)                     | §6      |
| Repository/handler query pattern notes                          | §7      |
| Registrar load pipeline impact summary                          | §8      |
| New findings register (expert review)                           | §14     |
| Report / balance query prerequisites                            | §15     |

---

## 11. Next steps (Track A continuation → #32)

1. **v1 target schema** — propose discriminator + single extension FK or consolidated accounts table.
2. **Tenancy decision (FR-02)** — choose FK-chain vs denormalized vs RLS; document in v3.
3. **Types identity (FR-15)** — include `owner_id` in hash or adopt composite unique.
4. **Ledger semantics (FR-05)** — support transfers as first-class or document two-line convention.
5. **Currency & balance (FR-07)** — add columns or computed views; align API spec (#33).
6. **Fix or bypass indexer DTO validation** — short-term patch before v3 if ingestion continues on v0.
7. **Regenerate ER diagram** after v3 on Docker Postgres / Supabase (#34).

---

## 12. Expert conceptual assessment (recommended v3 direction)

_Subject-matter view: personal finance data modeling + relational design. Informs #32; not a frozen spec._

### 12.1 What v0 gets right

- **Separation of plan vs actual** — `identified_transactions` (template) vs `transactions` (posted) matches budgeting/recurring use cases (FR-05).
- **Asset–liability pairing** — `financed_asset_accounts` correctly models encumbered assets (mortgage ↔ property) even if PK should be composite.
- **Soft delete + audit timestamps** on user-facing entities — appropriate for reloadable ingestion (FR-06).
- **Tenant column present** — right hook for isolation once strategy (FR-02) and types identity (FR-15) are fixed.

### 12.2 Core structural problems

1. **`accounts_indexer` as polymorphic hub** — Optimized for loader flexibility (PPT-022), not query simplicity or DB integrity. Finance apps read accounts far more often than they reshape subtypes; the hub penalizes the hot path.
2. **Class-table inheritance without shared PK** — `accounts.id`, `assets_accounts.id`, and `banking_asset_accounts.id` are **independent UUIDs** joined only through the indexer. There is no stable `account_id` on subtype rows — joins are mandatory and IDs proliferate.
3. **Cash-flow log without transfer semantics** — Personal finance requires transfers, CC payments, and loan draws. Single-sided rows with positive `value` are insufficient unless paired by convention outside the schema.
4. **Types table overloaded** — Serves COA classification (ASSETS/LIABILITIES), transaction categories, and indexer routing. API expects hierarchical income/expense categories — different abstraction.

### 12.3 Recommended target shape (v3 concept)

```
users
accounts (
  id, owner_id, name, account_kind ENUM,  -- CHECKING, SAVINGS, CREDIT_CARD, MORTGAGE, PROPERTY, ...
  currency, opened_at, closed_at,
  -- optional 1:1 extension keyed by account_id, not orphan UUID
)
account_extensions (account_id PK/FK, jsonb OR typed columns per kind — justify 3NF exception if jsonb)
types / categories (
  owner_id, classification, parent_id NULL, name,
  UNIQUE (owner_id, name)  -- drop global unique
)
transactions (
  id, owner_id, amount, currency, transaction_ts,
  transaction_kind ENUM,  -- INCOME, EXPENSE, TRANSFER
  from_account_id NULL, to_account_id NULL,
  category_id NULL, template_id NULL,
  CHECK transfer rules per kind
)
identified_transactions → rename or keep as transaction_templates
```

**Tenancy:** Keep denormalized `owner_id` on `transactions` and `accounts` only (hot filters); drop from subtype/extension tables; enforce via trigger or RLS on Supabase (Strategy B + C hybrid).

**Balances:** Materialized view `account_balances(owner_id, account_id, currency, balance, as_of)` refreshed from ledger — do not duplicate in API DTO without this view.

### 12.4 Intentional denormalizations to allow

| Denormalization                            | Rationale                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| `transactions.owner_id`                    | Tenant-scoped ledger scans without joining `accounts`                    |
| `types` global seed rows (`owner_id NULL`) | Shared COA templates for new users                                       |
| Snapshot `last_value` on accounts          | Performance for net-worth dashboard if reconciled nightly against ledger |

Document each in v3 freeze with reconciliation rule.

---

## 13. Expert review iteration log

| Iter   | Focus                   | Outcome                                                                         |
| ------ | ----------------------- | ------------------------------------------------------------------------------- |
| **1**  | Domain framing          | Added §1.1 domain context table; clarified PF vs GL positioning                 |
| **2**  | Ledger semantics        | Documented transfer rejection, sign convention, balance authority (§3.14, §4.5) |
| **3**  | Consolidation economics | Added subtype overlap analysis §4.6 (~70% shared columns)                       |
| **4**  | Code validation         | Confirmed indexer DTO bug §5.6; fixed UpserterFactory typo §7.5                 |
| **5**  | Concept & stop rule     | Added §12 expert v3 concept; consolidated findings in §14                       |
| **6**  | DTO validation defects  | NF-13, NF-14 — impossible defaults on liability/financed DTOs                   |
| **7**  | Tenancy asymmetry       | NF-15 — types write path lacks `OwnedTableRepository` enforcement               |
| **8**  | Domain rules            | NF-16, NF-17 — template type classification; recurring day cap at 28            |
| **9**  | Index & query planning  | NF-18, §15 report query prerequisites                                           |
| **10** | Plateau check           | NF-19, NF-20 — rate consistency, DTO-layer transaction XOR; **stopped**         |

**Stop criterion met (iteration 10):** Remaining observations (e.g. ISO 4217 seed table, audit column on indexer) are v3 implementation detail or duplicate §12 — marginal value below iteration 9 additions.

---

## 14. New findings register (expert review, 2026-07-05)

Findings discovered or upgraded during the ten-iteration expert review (finance + data modeling). Each entry is actionable for #32 / #33.

| ID        | Finding                                            | Severity     | Detail                                                                                  |
| --------- | -------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------- |
| **NF-01** | Transfers rejected at ingest                       | **High**     | Handler filters out rows with both `from_account_id` and `to_account_id` set — §3.14    |
| **NF-02** | Orphan transactions dropped                        | **Medium**   | Rows with neither account FK set after matching are removed — §3.14                     |
| **NF-03** | No transfer pair integrity                         | **High**     | Two manual single-sided rows; no schema link — §3.14, §4.5                              |
| **NF-04** | Indexer DTO blocks extended subtypes               | **Critical** | `_validate_linked_accounts()` always raises when extended FK populated — §5.6           |
| **NF-05** | No currency dimension                              | **High**     | All DECIMAL amounts unitless; cannot aggregate multi-currency — §4.5                    |
| **NF-06** | Dual balance authority                             | **High**     | Snapshot fields vs ledger with no reconciliation — §4.5                                 |
| **NF-07** | Decoupled subtype UUIDs                            | **Medium**   | `accounts.id` ≠ `assets_accounts.id` ≠ `banking_asset_accounts.id` — §12.2              |
| **NF-08** | `types` table overloaded                           | **Medium**   | COA + categories + indexer routing in one entity — §12.2                                |
| **NF-09** | API phantom fields                                 | **High**     | Spec expects `balance`, `currency`, `transaction_type`, category hierarchy — §1.1, §4.5 |
| **NF-10** | Implicit sign convention                           | **Low**      | Positive `value` only; direction from which FK is set — §3.14                           |
| **NF-11** | Subtype column overlap ~70%                        | **Medium**   | Consolidation candidate for v3 — §4.6                                                   |
| **NF-12** | `UpserterFactory` typo in prior draft              | **Info**     | Corrected in §7.5 (was `UpscribeFactory`)                                               |
| **NF-13** | `LiabilityAccountsDTO.total_paid` default          | **Critical** | `Field(gt=0, default=0)` — zero violates own validator — §14 NF-13                      |
| **NF-14** | `FinancedAssetAccountsDTO.financing_share` default | **Critical** | `= 0.0` with `gt=0` — same pattern — §14 NF-14                                          |
| **NF-15** | Types write path not owner-scoped                  | **High**     | `TypesRepository` extends `BaseRepository`; upsert without owner — §14 NF-15            |
| **NF-16** | Template type classification unchecked             | **Medium**   | `identified_transactions.type_id` may reference ASSETS/LIABILITIES types — §14 NF-16    |
| **NF-17** | Recurring day capped at 28                         | **Medium**   | Salaries on 29–31 unrepresentable — §14 NF-17                                           |
| **NF-18** | Ledger FK / report indexes missing                 | **Medium**   | No index on account FKs or `(owner_id, transaction_ts)` — §3.14, §15                    |
| **NF-19** | Dual interest rates uncorrelated                   | **Low**      | Monthly + yearly stored independently — §14 NF-19                                       |
| **NF-20** | Transaction XOR only in handler                    | **Medium**   | `TransactionsDTO` allows both/null FKs — API bypass — §14 NF-20                         |

### NF-01 — Transfers rejected at ingest

**Evidence:** `TransactionsHandler._match_accounts()` returns only rows where exactly one of `from_account_id` / `to_account_id` is non-null after matching.

**Finance impact:** Checking → savings, credit-card payment from cash, and loan disbursement to asset cannot be loaded as a single logical event. Net worth is unchanged on transfers but v0 cannot represent them atomically.

**v3 action:** Add `transaction_kind = TRANSFER` with both FKs populated and a CHECK constraint; update handler to stop filtering transfer rows (FR-05).

### NF-02 — Orphan transactions dropped

**Evidence:** Same filter removes rows where both FKs are null post-match (failed match or intentionally external row).

**Finance impact:** Valid use cases (pending categorization, external payee not modeled as account) are silently discarded during load rather than quarantined.

**v3 action:** Route unmatched rows to a staging table or `status = UNMATCHED` instead of dropping (FR-08).

### NF-03 — No transfer pair integrity

**Evidence:** No column on `transactions` links paired legs; `identified_transaction_id` is optional and template-scoped, not transfer-scoped.

**Finance impact:** Manual two-row transfers can drift (amount mismatch, one leg deleted) with no DB detection.

**v3 action:** `transfer_id UUID` shared by two rows, or single row with both FKs (preferred — see NF-01).

### NF-04 — Indexer DTO blocks extended subtypes

**Evidence:**

```187:201:modules/model/src/papita_txnsmodel/access/indexers/dto.py
        match self.asset_account, self.liability_account:
            case None, _:
                extended_account_type = ExtendedAssetAccountsDTO
            case _, None:
                extended_account_type = ExtendedLiabilityAccountsDTO
        extended_account_fields = [
            field_name
            for field_name, info in self.__class__.model_fields.items()
            if extended_account_type in get_args(info.annotation)
            or ExtendedLiabilityAccountsDTO in get_args(info.annotation)
        ]
        extended_accounts_count = sum(1 for field in extended_account_fields if getattr(self, field) is not None)
        if extended_accounts_count > 0:
            raise ValueError(f"Extended account is not of type {extended_account_type.__name__}")
```

**Defects:** (1) liability vs asset branch labels swapped; (2) field list always includes liability extended fields; (3) any populated extended field triggers raise.

**Finance impact:** Banking, mortgage, brokerage, and credit-card accounts may fail validation on ingest — subtypes either bypass DTO or never load.

**v3 action:** Fix validator short-term OR remove indexer DTO path in v3 (FR-03). Add regression test loading a `banking_asset_account` indexer row.

### NF-05 — No currency dimension

**Evidence:** Grep of `modules/model/src/papita_txnsmodel/model/` — no `currency` column on any table.

**Finance impact:** USD checking + EUR savings cannot be summed for net worth; FX gains/losses unmappable.

**v3 action:** `currency CHAR(3) NOT NULL` on `accounts` and `transactions` (ISO 4217); optional `exchange_rate` on cross-currency transfers (#33).

### NF-06 — Dual balance authority

**Evidence:** `assets_accounts.last_value` / `liability_accounts.present_value` vs ledger sum from `transactions` — no reconciliation job or constraint.

**Finance impact:** Dashboard can show stale net worth if snapshots are updated independently of posted transactions.

**v3 action:** Ledger-derived materialized view as canonical; snapshots optional with `as_of` timestamp (§12.3).

### NF-07 — Decoupled subtype UUIDs

**Evidence:** Class-table inheritance uses independent `uuid4` PKs on `accounts`, `assets_accounts`, and extension tables; linker is `accounts_indexer` only.

**Finance impact:** Every read/write touches the hub; ORM and API IDs multiply; "account id" is ambiguous in API design.

**v3 action:** Extension tables use `account_id` as PK/FK (1:1 with `accounts`).

### NF-08 — `types` table overloaded

**Evidence:** `TypesClassifications` spans ASSETS, LIABILITIES, TRANSACTIONS; same table backs indexer `type_id` and `identified_transactions.type_id`.

**Finance impact:** Category taxonomy (income/expense tree) conflated with balance-sheet classification — API `/categories` cannot map cleanly (FR-13).

**v3 action:** Split `account_types` vs `categories`, or add `parent_id` + `category_kind` on a renamed table (#33).

### NF-09 — API phantom fields

**Evidence:** #28 pain point #11 — API spec (PR #29) documents fields absent from SQLModel.

| API field                                             | v0 model              |
| ----------------------------------------------------- | --------------------- |
| `accounts.balance`, `initial_balance`, `currency`     | absent                |
| `categories.category_type`, `parent_id`               | absent (`types` flat) |
| `transactions.transaction_type`, `status`, `currency` | absent                |

**Finance impact:** #25 CRUD would invent columns or return fabricated values.

**v3 action:** Align spec in #33 or add columns/views in v3 schema (#32).

### NF-10 — Implicit sign convention

**Evidence:** `Transactions.value` has `gt=0`; outflow vs inflow determined solely by from vs to FK.

**Finance impact:** Refunds/chargebacks require careful FK placement; no explicit `DEBIT`/`CREDIT` for reporting exports.

**v3 action:** Optional `direction` enum or signed amount with documented convention.

### NF-11 — Subtype column overlap

**Evidence:** §4.6 — shared financial columns on `assets_accounts` and `liability_accounts` (~70% semantic overlap).

**Finance impact:** Higher migration cost and anomaly surface if v3 keeps six subtype tables.

**v3 action:** Consolidate shared columns onto `accounts` or single financial extension (FR-04).

### NF-13 — `LiabilityAccountsDTO.total_paid` impossible default

**Evidence:**

```60:60:modules/model/src/papita_txnsmodel/access/liabilities/dto.py
    total_paid: float = Field(gt=0, default=0, description="Total amount paid so far")
```

**Defect:** Pydantic rejects `total_paid=0` while default is `0`. New liability accounts cannot validate unless `total_paid` is omitted and default handling bypasses validation, or a positive value is always supplied.

**Finance impact:** Fresh loans (nothing paid yet) are the common case — the DTO fights the domain default.

**v3 action:** Use `Field(ge=0, default=0)` or make `total_paid` nullable until first payment.

### NF-14 — `FinancedAssetAccountsDTO.financing_share` impossible default

**Evidence:**

```99:99:modules/model/src/papita_txnsmodel/access/assets/dto.py
    financing_share: Annotated[float, Field(le=1, gt=0)] = 0.0
```

**Defect:** Default `0.0` violates `gt=0`. Model layer uses `default=1.0` — DTO and DAO defaults **diverge**.

**Finance impact:** Full financing (100% mortgage) fails DTO instantiation with defaults; partial financing requires explicit share on every load.

**v3 action:** Align DTO default with model (`1.0`) and use `gt=0` or `ge=0` with CHECK for open intervals.

### NF-15 — Types write path not owner-scoped

**Evidence:** `TypesRepository` extends `BaseRepository`, not `OwnedTableRepository`. `TypesService.create()` calls `_repository.upsert_record(parsed_obj, owner=owner)` but `BaseRepository.upsert_record` **ignores** `owner` — no tenant assignment or mismatch check.

Read path merges global + owned (`TypesRepository.get_records`). Write path can upsert any type row without binding to caller tenant.

**Finance impact:** User A could overwrite global type `"Groceries"` or User B's type if IDs collide (NF-04 / FR-15).

**v3 action:** Extend `TypesRepository.upsert_record` with owner rules, or split global types into read-only seed table.

### NF-16 — Template type classification unchecked

**Evidence:** `IdentifiedTransactionsService` uses `TypedEntitiesService` but does not assert `type.classification == TypesClassifications.TRANSACTIONS`. Indexer service **does** assert classification for accounts.

**Finance impact:** A recurring mortgage payment template could reference an ASSETS type — budget reports by category break.

**v3 action:** Service-level CHECK or FK to a `categories` view filtered to TRANSACTIONS classification.

### NF-17 — Recurring day capped at 28

**Evidence:** `planned_transaction_day` and `closing_day` use `le=28` on model and DTOs.

**Finance impact:** Payroll on the 31st, card cycles on the 30th, and month-end bills are clipped or must use day 28 as proxy — distorts cash-flow forecasting.

**v3 action:** Allow 1–31 with `last-day-of-month` flag, or store `rrule` / cron for v3 templates.

### NF-18 — Ledger FK and report indexes missing

**Evidence:** Seed migration indexes `transaction_ts` and (post #27) `owner_id` only. No indexes on `from_account_id`, `to_account_id`, `identified_transaction_id`.

**Finance impact:** `GET /reports/spending`, cash-flow, and balance views (#28 FR-12) scan full ledger per tenant.

**v3 action:** See §15 — add FK indexes + `(owner_id, transaction_ts DESC)` composite.

### NF-19 — Dual interest rates uncorrelated

**Evidence:** `assets_accounts` and `liability_accounts` store both `monthly_interest_rate` and `yearly_interest_rate` with no CHECK relating them (e.g. `(1 + r_m)^12 ≈ 1 + r_y` within tolerance).

**Finance impact:** Amortization vs APY displays can disagree; one field may be stale.

**v3 action:** Store one canonical rate + `rate_basis` enum (NOMINAL_MONTHLY, APY); derive the other.

### NF-20 — Transaction account XOR only in handler

**Evidence:** `TransactionsDTO` has no `@model_validator` for from/to XOR. Rule enforced only in `TransactionsHandler._match_accounts()` filter.

**Finance impact:** API or direct service calls can persist invalid rows (both accounts set, or neither) unless handler is always in path.

**v3 action:** DTO validator + DB CHECK mirroring intended `transaction_kind` (NF-01 / §12.3).

---

## 15. Report and balance query prerequisites (FR-12 input)

v0 schema lacks read models; these queries define **minimum indexes and joins** for #32 / #33.

### 15.1 Account balance (ledger-derived)

```sql
-- Per account, per tenant (single-sided convention)
SELECT a.id,
       COALESCE(SUM(CASE WHEN t.to_account_id = a.id THEN t.value END), 0)
     - COALESCE(SUM(CASE WHEN t.from_account_id = a.id THEN t.value END), 0) AS balance
FROM papita_transactions.accounts a
LEFT JOIN papita_transactions.transactions t
  ON t.owner_id = a.owner_id
 AND (t.from_account_id = a.id OR t.to_account_id = a.id)
 AND t.active = true
WHERE a.owner_id = :owner_id AND a.active = true
GROUP BY a.id;
```

**Blockers today:** NF-01 (transfers excluded from ingest); NF-05 (no currency — balance mixed-unit if ever multi-currency); NF-18 (FK indexes).

### 15.2 Spending by category (period)

```sql
SELECT ty.name, SUM(t.value) AS spent
FROM papita_transactions.transactions t
JOIN papita_transactions.identified_transactions it ON it.id = t.identified_transaction_id
JOIN papita_transactions.types ty ON ty.id = it.type_id
WHERE t.owner_id = :owner_id
  AND t.from_account_id IS NOT NULL
  AND t.transaction_ts BETWEEN :start AND :end
  AND t.active = true
GROUP BY ty.name;
```

**Blockers:** NF-08 (types overloaded); NF-16 (wrong classification possible); optional link — many transactions have `identified_transaction_id IS NULL`.

### 15.3 Recommended v3 indexes (reports)

| Index                                          | Serves                                  |
| ---------------------------------------------- | --------------------------------------- |
| `(owner_id, transaction_ts)` on `transactions` | All time-series reports                 |
| `(from_account_id)` on `transactions`          | Outflow / balance                       |
| `(to_account_id)` on `transactions`            | Inflow / balance                        |
| `(owner_id, classification)` on `types`        | Category filters                        |
| `(owner_id, name)` UNIQUE on `types`           | Tenant taxonomy (replace global unique) |

Materialized view candidate: `account_balances` refreshed on transaction upsert (FR-12).

---

- Parent issue: [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
- Sub-issues: [#30](https://github.com/Elmorralito/save-ma-money/issues/30) (this doc), [#32](https://github.com/Elmorralito/save-ma-money/issues/32) (v1–v3 schema)
- Models: [`modules/model/src/papita_txnsmodel/model/`](../../modules/model/src/papita_txnsmodel/model/)
- Migrations: [`modules/model/alembic/versions/`](../../modules/model/alembic/versions/)
- Handlers: [`modules/model/src/papita_txnsmodel/handlers/`](../../modules/model/src/papita_txnsmodel/handlers/)
- ER (stale): [`docs/postgres_papita_transactions.png`](../postgres_papita_transactions.png)
- Requirements: [`docs/issues/PPT-031-simplify-requirements.md`](../issues/PPT-031-simplify-requirements.md)
