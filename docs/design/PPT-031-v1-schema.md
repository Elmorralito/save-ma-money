# PPT-031 v1–v3: Target Schema Design

| Field        | Value                                                                                                                      |
| ------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **Issue**    | [#32 — Target schema iterations v1–v3 + ER diagram](https://github.com/Elmorralito/save-ma-money/issues/32)                |
| **Parent**   | [#28 — refactor/PPT-031: Simplify data model and align API design](https://github.com/Elmorralito/save-ma-money/issues/28) |
| **Input**    | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) + [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md)               |
| **Track**    | A — Steps A2–A4                                                                                                            |
| **Platform** | PostgreSQL via Supabase (DuckDB out of scope)                                                                              |
| **Date**     | 2026-07-06                                                                                                                 |
| **Status**   | v3 **proposed for G1 sign-off** — not yet approved                                                                         |

---

## Document map

| Section                                         | Track step | Purpose                                                                           |
| ----------------------------------------------- | ---------- | --------------------------------------------------------------------------------- |
| [§1 v1](#1-v1-draft-target-schema)              | A2         | Draft simplification + open decisions                                             |
| [§2 v2](#2-v2-revised-schema-api-domain-review) | A3         | API domain alignment (categories, movements)                                      |
| [§3 v3](#3-v3-frozen-target-schema)             | A4         | Frozen schema for implementation                                                  |
| [§4](#4-er-diagram-v3)                          | A4         | ER diagram (mermaid + SVG)                                                        |
| [§5](#5-alembic-migration-outline)              | A4         | DDL-only migration outline                                                        |
| [§6](#6-intentional-denormalizations)           | A4         | Documented 3NF exceptions                                                         |
| [§7](#7-sign-off-checklist-g1)                  | A4         | Maintainer gate for [#28](https://github.com/Elmorralito/save-ma-money/issues/28) |
| [v4 extensions](PPT-031-v4-extensions.md)       | Post-G1    | Budgets, splits, recurrence, reconciliation, etc.                                 |

### FR / NF traceability

| Requirement                 | v1                     | v2               | v3 resolution                            |
| --------------------------- | ---------------------- | ---------------- | ---------------------------------------- |
| FR-01 (3NF)                 | Options evaluated      | Partial          | §3 + §6 exceptions                       |
| FR-02 (tenancy)             | Three strategies       | Hybrid chosen    | Strategy B+C hybrid                      |
| FR-03 (indexer)             | Remove hub             | —                | `accounts_indexer` dropped               |
| FR-04 (subtypes)            | Consolidation proposal | —                | Base on `accounts` + 1:1 extensions      |
| FR-05 (templates vs posted) | Keep split             | API mapping      | `transaction_templates` + `transactions` |
| FR-06 (audit fields)        | Required on all tables | —                | All tables extend `BaseSQLModel`         |
| FR-09 (budgets)             | Defer vs add           | Defer MVP        | **Deferred** — v2 API                    |
| FR-12 (reports)             | View strategy          | —                | `account_balances` materialized view     |
| FR-14 (legacy backfill)     | —                      | —                | §5 migration outline                     |
| FR-15 (types identity)      | Options                | Categories split | Composite unique on `categories`         |
| FR-16 (financed assets)     | PK options             | —                | Composite PK + CHECK constraints         |
| NF-01–NF-03 (transfers)     | —                      | Movements mapped | `transaction_kind = TRANSFER`            |
| NF-05 (currency)            | Add columns            | API align        | `currency` on accounts + transactions    |
| NF-09 (phantom fields)      | —                      | Field mapping    | Balance via view; categories table       |

---

## 1. v1 — Draft target schema

### 1.1 Design goals

v1 proposes structural simplification informed by v0 audit §11–§12 and NF register §14. It **does not** freeze API naming or budgets scope — those are v2 inputs.

| v0 problem                                              | v1 direction                                                                                                 | FR            |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------- |
| `accounts_indexer` 8-FK sparse matrix                   | Eliminate hub; `account_kind` discriminator on `accounts`                                                    | FR-03         |
| Six subtype tables + two base tables                    | Merge ~70% shared financial columns onto `accounts`; 1:1 extension tables keyed by `account_id`              | FR-04         |
| `types` overloaded (COA + categories + indexer routing) | Split: `account_kind` enum replaces account-side `types`; new `categories` table for income/expense taxonomy | FR-13 (draft) |
| Single-sided transactions; transfers rejected           | `transaction_kind` enum with `TRANSFER` allowing both account FKs                                            | FR-05, NF-01  |
| Redundant `owner_id` on 13 tables                       | Evaluate tenancy strategies (§1.3)                                                                           | FR-02         |
| No currency                                             | `currency CHAR(3)` on monetary entities                                                                      | NF-05         |

### 1.2 v1 entity sketch

```
users
accounts (account_kind, ledger_side, currency, consolidated financial columns)
  ├── banking_account_details      (account_id PK/FK, 0..1)
  ├── real_estate_account_details  (account_id PK/FK, 0..1)
  ├── trading_account_details      (account_id PK/FK, 0..1)
  ├── credit_card_account_details  (account_id PK/FK, 0..1)
  ├── loan_account_details         (account_id PK/FK, 0..1)
  └── account_financing            (asset_account_id + loan_account_id composite PK)
categories (parent_id, category_kind: INCOME|EXPENSE)
transaction_templates (was identified_transactions)
transactions (transaction_kind: INCOME|EXPENSE|TRANSFER)
account_balances (materialized view — read model)
```

**Dropped in v1 proposal:** `accounts_indexer`, `types`, `assets_accounts`, `liability_accounts`, and all six legacy extension tables.

### 1.3 Tenancy strategy options (FR-02)

| Strategy             | Mechanism                                                                                         | Pros                                                  | Cons                                                                         | v1 recommendation                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **A — FK chain**     | Drop child `owner_id`; filter via `accounts.owner_id` joins                                       | Single source of truth; fewer update anomalies        | Every transaction list joins `accounts`; global categories need special case | Reject as sole strategy — too expensive for ledger hot path                                          |
| **B — Denormalized** | Keep `owner_id` on hot tables (`accounts`, `transactions`, `categories`, `transaction_templates`) | Fast tenant scans; matches PR #27 repository patterns | Must enforce consistency on write                                            | **Adopt** for hot tables                                                                             |
| **C — RLS**          | Postgres `owner_id = current_setting('app.user_id')` policies                                     | DB-enforced isolation (defense in depth)              | Supabase-specific ops; doubles filter logic with app layer                   | **Defer to B3** ([#31](https://github.com/Elmorralito/save-ma-money/issues/31)); document as Phase 2 |

**v1 preferred:** **B + optional C later** — denormalized `owner_id` on tenant-scoped hot tables; drop `owner_id` from 1:1 extension tables (derivable via `account_id → accounts.owner_id`). Enforce cross-table consistency with CHECK constraints and service validators until RLS is adopted.

### 1.4 Account consolidation (FR-03, FR-04)

#### Account kind discriminator

Replace indexer routing with `account_kind` enum on `accounts`:

| `account_kind`         | `ledger_side` | Extension table               | v0 source tables          |
| ---------------------- | ------------- | ----------------------------- | ------------------------- |
| `CHECKING`             | ASSET         | `banking_account_details`     | assets + banking          |
| `SAVINGS`              | ASSET         | `banking_account_details`     | assets + banking          |
| `CASH`                 | ASSET         | —                             | assets only               |
| `INVESTMENT_BROKERAGE` | ASSET         | `trading_account_details`     | assets + trading          |
| `REAL_ESTATE`          | ASSET         | `real_estate_account_details` | assets + real_estate      |
| `CREDIT_CARD`          | LIABILITY     | `credit_card_account_details` | liabilities + credit_card |
| `LOAN_MORTGAGE`        | LIABILITY     | `loan_account_details`        | liabilities + bank_credit |
| `OTHER_ASSET`          | ASSET         | —                             | assets only               |
| `OTHER_LIABILITY`      | LIABILITY     | —                             | liabilities only          |

**Extension rule:** At most one extension row per account; enforced by separate 1:1 tables (not sparse FK matrix). `account_kind` determines which extension table may exist — validated in service layer + optional trigger.

#### Consolidated financial columns on `accounts`

Shared columns from `assets_accounts` / `liability_accounts` (~70% overlap per v0 §4.6):

| Column                | Asset kinds | Liability kinds | Notes                                   |
| --------------------- | ----------- | --------------- | --------------------------------------- |
| `initial_value`       | ✓           | ✓               | Opening principal / cost basis          |
| `current_value`       | ✓           | ✓               | Replaces `last_value` / `present_value` |
| `months_per_period`   | ✓           | ✓               | Amortization / valuation period         |
| `interest_rate`       | ✓           | ✓               | **Single canonical rate** (NF-19)       |
| `interest_rate_basis` | ✓           | ✓               | `NOMINAL_MONTHLY` \| `APY`              |
| `periodic_payment`    | —           | ✓               | Replaces `payment`                      |
| `total_paid`          | —           | ✓               | `ge=0`, default 0 (NF-13 fix)           |
| `overall_periods`     | —           | ✓               |                                         |
| `periods_paid`        | —           | ✓               |                                         |
| `closing_day`         | —           | ✓               | 1–31 (NF-17 fix)                        |
| `roi`                 | ✓           | —               | Optional performance metric             |
| `periodic_earnings`   | ✓           | —               |                                         |

### 1.5 Transaction semantics (FR-05)

**Decision (v1):** Keep **two tables** — templates vs posted ledger.

| Table                   | Role                        | v0 equivalent             |
| ----------------------- | --------------------------- | ------------------------- |
| `transaction_templates` | Recurring / planned entries | `identified_transactions` |
| `transactions`          | Posted activity             | `transactions`            |

**`transaction_kind` on posted rows:**

| Kind       | `from_account_id` | `to_account_id` | `category_id` | Semantics                       |
| ---------- | ----------------- | --------------- | ------------- | ------------------------------- |
| `INCOME`   | NULL              | required        | required      | Inflow to account               |
| `EXPENSE`  | required          | NULL            | required      | Outflow from account            |
| `TRANSFER` | required          | required        | NULL          | Between accounts, same currency |

Replaces handler-only XOR rule (NF-20) with DTO + DB CHECK constraints.

### 1.6 Types / categories split (FR-13 draft)

| v0 `types` role                                 | v1 target                                            |
| ----------------------------------------------- | ---------------------------------------------------- |
| ASSETS / LIABILITIES classification for indexer | `account_kind` + `ledger_side` on `accounts`         |
| TRANSACTIONS classification for templates       | `categories` with `category_kind` (INCOME / EXPENSE) |
| Global vs user-scoped taxonomy                  | `categories.owner_id` nullable; composite unique     |

### 1.7 Financed assets (FR-16 draft)

Rename `financed_asset_accounts` → `account_financing`:

- **PK:** `(asset_account_id, loan_account_id)` composite (fixes v0 2NF issue)
- **CHECK:** `financing_share > 0 AND financing_share <= 1`
- **CHECK:** asset `ledger_side = ASSET`, loan `ledger_side = LIABILITY`
- **CHECK:** `asset.owner_id = loan.owner_id = account_financing.owner_id`

### 1.8 v1 open decisions table

| ID   | Decision                 | Options                                                            | v1 lean                                                  | Resolved in |
| ---- | ------------------------ | ------------------------------------------------------------------ | -------------------------------------------------------- | ----------- |
| D-01 | Tenancy enforcement      | B only vs B+C RLS                                                  | B now, C optional                                        | v3 §3.2     |
| D-02 | Balance source of truth  | Ledger view vs snapshot                                            | Ledger view canonical; `current_value` optional snapshot | v3 §3.5     |
| D-03 | Budgets in schema        | Add tables vs defer API                                            | Defer (FR-09)                                            | v2 §2.3     |
| D-04 | API `/categories` naming | Rename to `/categories` vs keep `/types`                           | Expose `/categories` → `categories` table                | v2 §2.1     |
| D-05 | API `/movements`         | Separate table vs `TRANSFER` rows                                  | `TRANSFER` transactions + status field                   | v2 §2.2     |
| D-06 | Transaction splits       | `transaction_splits` table vs defer                                | Defer post-MVP                                           | v2 §2.4     |
| D-07 | Global category seeds    | `owner_id NULL` rows vs per-user copy on register                  | Nullable `owner_id` seeds                                | v3 §3.4     |
| D-08 | Tags storage             | PostgreSQL ARRAY vs junction table                                 | Keep ARRAY (1NF acceptable per v0 §4.1)                  | v3          |
| D-09 | Interest rate storage    | Dual monthly+yearly vs single canonical                            | Single rate + basis enum                                 | v3 §3.3     |
| D-10 | Legacy `types` FK remap  | Map TRANSACTIONS types → categories; drop ASSETS/LIABILITIES types | Migration backfill script                                | v3 §5       |

---

## 2. v2 — Revised schema (API domain review)

v2 incorporates API vocabulary from `modules/api/API_Endpoints.md.md`. Full endpoint mapping delivered in [`PPT-031-api-model-mapping.md`](PPT-031-api-model-mapping.md) ([#33](https://github.com/Elmorralito/save-ma-money/issues/33)).

### 2.1 Categories vs `types` (FR-13)

| API field       | v3 column                             | Notes                                      |
| --------------- | ------------------------------------- | ------------------------------------------ |
| `id`            | `categories.id`                       | UUID; hash includes `owner_id` (FR-15)     |
| `name`          | `categories.name`                     |                                            |
| `category_type` | `categories.category_kind`            | `income` → `INCOME`, `expense` → `EXPENSE` |
| `parent_id`     | `categories.parent_id`                | Self-FK; hierarchy supported               |
| `icon`, `color` | `categories.icon`, `categories.color` | New columns (absent in v0)                 |
| `is_active`     | `categories.active`                   | BaseSQLModel                               |
| `subcategories` | API computed                          | Not stored — child rows via `parent_id`    |

**API route decision:** Keep `/categories/*` in spec; map to `categories` table. Deprecate v0 `/types` concept for API consumers. Resolved in [`PPT-031-api-model-mapping.md`](PPT-031-api-model-mapping.md) §4.2 and [`API_Endpoints.md.md`](../../modules/api/API_Endpoints.md.md) (breaking-change notice in mapping §8).

**v0 `types` migration:**

| `types.classification` | v3 destination                                                       |
| ---------------------- | -------------------------------------------------------------------- |
| `TRANSACTIONS`         | `categories` (category_kind from name heuristics or default EXPENSE) |
| `ASSETS`               | Dropped — `account_kind` on accounts                                 |
| `LIABILITIES`          | Dropped — `account_kind` on accounts                                 |

### 2.2 Movements vs transactions (FR-05, NF-01)

API `/movements/*` describes **inter-account transfers**. v2 maps movements to **`transactions` where `transaction_kind = TRANSFER`**.

| API movement field       | v3 `transactions` column                            | Notes                                   |
| ------------------------ | --------------------------------------------------- | --------------------------------------- |
| `source_account_id`      | `from_account_id`                                   |                                         |
| `destination_account_id` | `to_account_id`                                     |                                         |
| `amount`                 | `amount`                                            | Always positive                         |
| `currency`               | `currency`                                          | Must match both accounts                |
| `movement_date`          | `transaction_ts`                                    |                                         |
| `status`                 | `status`                                            | `PENDING` \| `COMPLETED` \| `CANCELLED` |
| `scheduled`              | `status = PENDING`                                  |                                         |
| `execute` endpoint       | Update `status` → `COMPLETED`, set `transaction_ts` |                                         |

**API route decision:** Implement `/movements/*` as a **router alias** over transfer transactions (filter `transaction_kind = TRANSFER`). Do **not** create a `movements` table. Resolved in [`PPT-031-api-model-mapping.md`](PPT-031-api-model-mapping.md) §5.7 — alias router; `GET /transactions` excludes TRANSFER by default; filter `?transaction_type=transfer` also supported.

### 2.3 Budgets (FR-09)

API defines full `/budgets/*` CRUD with allocations. v0 has **no** budget tables.

**v2 decision: DEFER budgets from v3 G1 MVP** — full design in [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) §4.1 (v4.1 migration).

| Aspect                            | Decision                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------- |
| v3 tables                         | None at G1 — see v4.1 in [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) |
| API spec                          | Mark `/budgets/*` as **v2 API** (post-MVP); return 501 or hide from MVP OpenAPI |
| `GET /reports/budget-performance` | Deferred with budgets (FR-12)                                                   |
| `transactions.budget_id`          | **Not added** in v3 — API phantom field removed for MVP                         |

**Rationale:** Budgets require `budgets` + `budget_allocations` + period semantics + spent aggregation. Adding them delays G1 freeze without blocking core ledger CRUD. Revisit in post-v3 design issue.

### 2.4 Other API field resolutions

| API field                              | v3 resolution                                             | MVP?         |
| -------------------------------------- | --------------------------------------------------------- | ------------ |
| `accounts.balance`                     | `account_balances` materialized view                      | ✓ (read)     |
| `accounts.initial_balance`             | `accounts.initial_value`                                  | ✓            |
| `accounts.currency`                    | `accounts.currency`                                       | ✓            |
| `transactions.transaction_type`        | `transaction_kind` + category for income/expense          | ✓            |
| `transactions.account_id`              | Derived: `to_account_id` if INCOME else `from_account_id` | ✓ (API DTO)  |
| `transactions.description`             | `transactions.description` (new column)                   | ✓            |
| `transactions.is_recurring`            | `template_id IS NOT NULL`                                 | ✓ (computed) |
| `transactions.recurrence_rule`         | Deferred — templates use `planned_day`                    | Post-MVP     |
| `transactions.split`                   | Deferred — no `transaction_splits` table in v3            | Post-MVP     |
| `transactions.budget_id`               | Removed (budgets deferred)                                | —            |
| `transactions.reference_number`        | `transactions.reference_number`                           | ✓            |
| `transactions.attachments`, `metadata` | Deferred (JSONB or separate table)                        | Post-MVP     |

### 2.5 v2 API ↔ v3 table summary

| API resource                  | v3 table(s)                             | MVP scope          |
| ----------------------------- | --------------------------------------- | ------------------ |
| `/accounts/*`                 | `accounts` + extensions                 | ✓                  |
| `/categories/*`               | `categories`                            | ✓                  |
| `/transactions/*`             | `transactions`, `transaction_templates` | ✓                  |
| `/movements/*`                | `transactions` (TRANSFER)               | ✓ (alias)          |
| `/budgets/*`                  | —                                       | **Deferred**       |
| `/reports/spending`           | `transactions` + `categories`           | ✓ (query)          |
| `/reports/cash-flow`          | `transactions` + `accounts`             | ✓ (query)          |
| `/reports/trends`             | `transactions`                          | ✓ (query)          |
| `/reports/budget-performance` | —                                       | **Deferred**       |
| `/reports/export`             | Above queries                           | ✓ (stub format OK) |

---

## 3. v3 — Frozen target schema

> **Status:** Proposed for **G1 sign-off** on [#28](https://github.com/Elmorralito/save-ma-money/issues/28). Not approved for implementation until maintainer comment.

### 3.1 Table inventory (11 tables + 1 view)

| #   | Table                          | Extends BaseSQLModel | Tenant-scoped           |
| --- | ------------------------------ | -------------------- | ----------------------- |
| 1   | `users`                        | ✓                    | root                    |
| 2   | `accounts`                     | ✓                    | ✓ (`owner_id`)          |
| 3   | `banking_account_details`      | ✓                    | via `account_id`        |
| 4   | `real_estate_account_details`  | ✓                    | via `account_id`        |
| 5   | `trading_account_details`      | ✓                    | via `account_id`        |
| 6   | `credit_card_account_details`  | ✓                    | via `account_id`        |
| 7   | `loan_account_details`         | ✓                    | via `account_id`        |
| 8   | `account_financing`            | ✓                    | ✓ (`owner_id`)          |
| 9   | `categories`                   | ✓                    | ✓ (`owner_id` nullable) |
| 10  | `transaction_templates`        | ✓                    | ✓ (`owner_id`)          |
| 11  | `transactions`                 | ✓                    | ✓ (`owner_id`)          |
| —   | `account_balances` (mat. view) | —                    | ✓                       |

**Dropped tables (14 → 11):** `accounts_indexer`, `types`, `assets_accounts`, `liability_accounts`, `banking_asset_accounts`, `real_estate_asset_accounts`, `trading_asset_accounts`, `bank_credit_liability_accounts`, `credit_card_liability_accounts`, `identified_transactions`, `financed_asset_accounts`.

### 3.2 Tenancy model (FR-02 — resolved D-01)

**Frozen strategy: B (denormalized hot paths), RLS deferred (B3).**

| Table                   | `owner_id` | Enforcement                               |
| ----------------------- | ---------- | ----------------------------------------- |
| `users`                 | —          | root                                      |
| `accounts`              | NOT NULL   | `OwnedTableRepository` + API dependency   |
| `account_financing`     | NOT NULL   | CHECK matches linked accounts             |
| `categories`            | NULLABLE   | NULL = global seed; NOT NULL = user-owned |
| `transaction_templates` | NOT NULL   | Repository                                |
| `transactions`          | NOT NULL   | CHECK matches account owners              |
| Extension tables        | **absent** | Derived via `accounts.owner_id`           |

**Cross-tenant denial tests required (NFR-04):** accounts, categories, transactions minimum.

### 3.3 Column definitions

#### `users` — unchanged from v0

Same columns as v0 §3.1.

#### `accounts`

| Column                                             | Type          | Nullable | Constraints / notes              |
| -------------------------------------------------- | ------------- | -------- | -------------------------------- |
| `id`                                               | UUID          | NO       | PK, default uuid4                |
| `owner_id`                                         | UUID          | NO       | FK → `users.id`                  |
| `name`                                             | VARCHAR(255)  | NO       |                                  |
| `description`                                      | TEXT          | NO       | default `''`                     |
| `tags`                                             | VARCHAR[]     | NO       | default `{}`                     |
| `account_kind`                                     | ENUM          | NO       | See §3.3.1                       |
| `ledger_side`                                      | ENUM          | NO       | `ASSET` \| `LIABILITY`           |
| `currency`                                         | CHAR(3)       | NO       | ISO 4217, default `USD`          |
| `opened_at`                                        | TIMESTAMP     | NO       | was `start_ts`                   |
| `closed_at`                                        | TIMESTAMP     | YES      | was `end_ts`                     |
| `initial_value`                                    | DECIMAL(22,8) | YES      | `ge=0`                           |
| `current_value`                                    | DECIMAL(22,8) | YES      | `ge=0`; optional snapshot (D-02) |
| `current_value_as_of`                              | TIMESTAMP     | YES      | Required if `current_value` set  |
| `months_per_period`                                | SMALLINT      | YES      | default 1, `gt=0`                |
| `interest_rate`                                    | DECIMAL(10,6) | YES      | Canonical rate (D-09)            |
| `interest_rate_basis`                              | ENUM          | YES      | `NOMINAL_MONTHLY` \| `APY`       |
| `periodic_payment`                                 | DECIMAL(22,8) | YES      | Liability kinds                  |
| `total_paid`                                       | DECIMAL(22,8) | YES      | `ge=0`, default 0                |
| `overall_periods`                                  | SMALLINT      | YES      |                                  |
| `periods_paid`                                     | SMALLINT      | YES      |                                  |
| `closing_day`                                      | SMALLINT      | YES      | 1–31                             |
| `roi`                                              | DECIMAL(10,4) | YES      |                                  |
| `periodic_earnings`                                | DECIMAL(22,8) | YES      |                                  |
| `active`, `deleted_at`, `created_at`, `updated_at` | —             | —        | BaseSQLModel                     |

**Indexes:** `(owner_id)`, `(owner_id, account_kind)`, `(name)`, `(opened_at)`, `(closed_at)`

##### 3.3.1 `account_kind` enum

`CHECKING`, `SAVINGS`, `CASH`, `INVESTMENT_BROKERAGE`, `REAL_ESTATE`, `CREDIT_CARD`, `LOAN_MORTGAGE`, `OTHER_ASSET`, `OTHER_LIABILITY`

**CHECK `accounts_ledger_side_matches_kind`:** `ledger_side` consistent with kind (e.g. `CREDIT_CARD` → `LIABILITY`).

#### Extension tables (1:1, `account_id` PK/FK → `accounts.id`)

**`banking_account_details`:** `entity` VARCHAR NOT NULL, `account_number` VARCHAR NULL

**`real_estate_account_details`:** `address`, `city`, `country` VARCHAR NOT NULL; `total_area`, `built_area` DECIMAL(12,4) NOT NULL; `area_unit` ENUM; `ownership` ENUM (`FULL`/`PARTIAL`); `participation` DECIMAL(4,4) default 1.0

**`trading_account_details`:** `buy_value` DECIMAL(22,8) NOT NULL; `units` SMALLINT NOT NULL default 1

**`credit_card_account_details`:** `credit_limit` DECIMAL(22,8) NOT NULL

**`loan_account_details`:** `is_paid_off` BOOLEAN NOT NULL default false; `insurance_payment`, `extras_payment` DECIMAL(22,8) NOT NULL default 0

#### `account_financing` (FR-16)

| Column             | Type         | Notes                                 |
| ------------------ | ------------ | ------------------------------------- |
| `asset_account_id` | UUID         | PK (composite), FK → `accounts.id`    |
| `loan_account_id`  | UUID         | PK (composite), FK → `accounts.id`    |
| `financing_share`  | DECIMAL(4,4) | NOT NULL, `gt=0`, `le=1`, default 1.0 |
| `owner_id`         | UUID         | NOT NULL, FK → `users.id`             |
| audit columns      | —            | BaseSQLModel                          |

**Constraints:**

- `pk_account_financing`: PRIMARY KEY (`asset_account_id`, `loan_account_id`)
- `chk_financing_owner_consistency`: `owner_id` matches both accounts' `owner_id`
- `chk_financing_ledger_sides`: asset account `ledger_side = ASSET`, loan `ledger_side = LIABILITY`

#### `categories` (FR-13, FR-15)

| Column          | Type         | Nullable | Notes                                              |
| --------------- | ------------ | -------- | -------------------------------------------------- |
| `id`            | UUID         | NO       | PK; uuid5 from `owner_id \| name \| category_kind` |
| `owner_id`      | UUID         | YES      | FK → `users.id`; NULL = global seed                |
| `parent_id`     | UUID         | YES      | FK → `categories.id`                               |
| `name`          | VARCHAR(255) | NO       |                                                    |
| `category_kind` | ENUM         | NO       | `INCOME` \| `EXPENSE`                              |
| `description`   | TEXT         | NO       | default `''`                                       |
| `tags`          | VARCHAR[]    | NO       |                                                    |
| `icon`          | VARCHAR(64)  | YES      |                                                    |
| `color`         | VARCHAR(7)   | YES      | hex `#RRGGBB`                                      |
| audit columns   | —            | —        | BaseSQLModel                                       |

**Unique:** `UNIQUE (COALESCE(owner_id, '00000000-0000-0000-0000-000000000000'), COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'), name, category_kind)` — siblings under different parents may share a name; root vs child with same name are distinct via `parent_id`

**Indexes:** `(owner_id)`, `(parent_id)`, `(owner_id, category_kind)`

#### `transaction_templates` (FR-05)

| Column           | Type          | Notes                                                                           |
| ---------------- | ------------- | ------------------------------------------------------------------------------- |
| `id`             | UUID          | PK                                                                              |
| `owner_id`       | UUID          | FK → `users.id`                                                                 |
| `category_id`    | UUID          | FK → `categories.id`; must reference EXPENSE or INCOME matching template intent |
| `name`           | VARCHAR       |                                                                                 |
| `description`    | TEXT          |                                                                                 |
| `tags`           | VARCHAR[]     |                                                                                 |
| `planned_amount` | DECIMAL(22,8) | `gt=0`                                                                          |
| `planned_day`    | SMALLINT      | 1–31 (NF-17 resolved)                                                           |
| `use_month_end`  | BOOLEAN       | default false; when true, `planned_day` ignored                                 |
| audit columns    | —             | BaseSQLModel                                                                    |

**Service rule (NF-16):** `category.category_kind` must be `EXPENSE` or `INCOME` (not enforced by FK alone).

#### `transactions`

| Column             | Type          | Nullable     | Notes                                                        |
| ------------------ | ------------- | ------------ | ------------------------------------------------------------ |
| `id`               | UUID          | NO           | PK                                                           |
| `owner_id`         | UUID          | NO           | FK → `users.id`                                              |
| `transaction_kind` | ENUM          | NO           | `INCOME` \| `EXPENSE` \| `TRANSFER`                          |
| `amount`           | DECIMAL(22,8) | NO           | `gt=0`                                                       |
| `currency`         | CHAR(3)       | NO           | Must match account currency for TRANSFER                     |
| `transaction_ts`   | TIMESTAMP     | NO           |                                                              |
| `from_account_id`  | UUID          | YES          | FK → `accounts.id`                                           |
| `to_account_id`    | UUID          | YES          | FK → `accounts.id`                                           |
| `category_id`      | UUID          | YES          | FK → `categories.id`                                         |
| `template_id`      | UUID          | YES          | FK → `transaction_templates.id`                              |
| `status`           | ENUM          | NO           | `PENDING` \| `COMPLETED` \| `CANCELLED`; default `COMPLETED` |
| `description`      | TEXT          | NO           | default `''`                                                 |
| `reference_number` | VARCHAR(64)   | YES          |                                                              |
| `tags`             | VARCHAR[]     | NO           |                                                              |
| audit columns      | —             | BaseSQLModel |

**CHECK `chk_transaction_kind_accounts`:**

```sql
(transaction_kind = 'INCOME'  AND from_account_id IS NULL AND to_account_id IS NOT NULL AND category_id IS NOT NULL)
OR (transaction_kind = 'EXPENSE' AND from_account_id IS NOT NULL AND to_account_id IS NULL AND category_id IS NOT NULL)
OR (transaction_kind = 'TRANSFER' AND from_account_id IS NOT NULL AND to_account_id IS NOT NULL AND category_id IS NULL
    AND from_account_id <> to_account_id)
```

**CHECK `chk_transaction_owner_accounts`:** `owner_id` equals `from` and/or `to` account `owner_id`.

**Indexes (NF-18):** `(owner_id, transaction_ts DESC)`, `(from_account_id)`, `(to_account_id)`, `(category_id)`, `(template_id)`, `(owner_id, transaction_kind)`

#### `account_balances` (materialized view — FR-12)

```sql
CREATE MATERIALIZED VIEW papita_transactions.account_balances AS
SELECT
    a.owner_id,
    a.id AS account_id,
    a.currency,
    COALESCE(SUM(CASE WHEN t.to_account_id = a.id AND t.status = 'COMPLETED' THEN t.amount END), 0)
  - COALESCE(SUM(CASE WHEN t.from_account_id = a.id AND t.status = 'COMPLETED' THEN t.amount END), 0) AS balance,
    MAX(t.transaction_ts) AS last_activity_ts
FROM papita_transactions.accounts a
LEFT JOIN papita_transactions.transactions t
  ON t.owner_id = a.owner_id
 AND (t.from_account_id = a.id OR t.to_account_id = a.id)
 AND t.active = true
WHERE a.active = true
GROUP BY a.owner_id, a.id, a.currency;

CREATE UNIQUE INDEX ON papita_transactions.account_balances (owner_id, account_id);
```

Refresh strategy: `REFRESH MATERIALIZED VIEW CONCURRENTLY` on transaction upsert batch or scheduled job ([#34](https://github.com/Elmorralito/save-ma-money/issues/34) runbook).

### 3.4 Categories identity rules (FR-15 — resolved D-07)

| Rule          | Implementation                                                                                         |
| ------------- | ------------------------------------------------------------------------------------------------------ |
| ID generation | `uuid5(NAMESPACE_URL, sha256(f"{owner_id or 'global'}_{parent_id or 'root'}_{name}_{category_kind}"))` |
| Uniqueness    | Composite unique on `(owner_id coalesced, parent_id coalesced, name, category_kind)`                   |
| Global seeds  | `owner_id IS NULL`; read-only for tenants; copied on register optional post-MVP                        |
| Write scoping | `CategoriesRepository` extends `OwnedTableRepository` with NULL-owner admin path for seeds             |
| Cross-tenant  | User cannot upsert global category; distinct names per tenant allowed                                  |

### 3.5 Balance authority (resolved D-02)

| Source                   | Role                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `account_balances` view  | **Canonical** for API `balance` and reports                                         |
| `accounts.current_value` | Optional snapshot for illiquid assets (real estate); must set `current_value_as_of` |
| Reconciliation           | Nightly job flags accounts where `abs(current_value - balance) > tolerance`         |

### 3.6 3NF compliance summary (FR-01)

| Area                               | Status      | Notes                             |
| ---------------------------------- | ----------- | --------------------------------- |
| Redundant `owner_id` on extensions | ✓ Resolved  | Dropped from 1:1 tables           |
| `owner_id` on `transactions`       | △ Exception | Documented §6 — query performance |
| `owner_id` on `account_financing`  | △ Exception | Documented §6 — join avoidance    |
| `current_value` snapshot           | △ Exception | Documented §6 — illiquid assets   |
| Global category seeds              | △ Exception | Documented §6 — onboarding        |
| Sparse FK matrix                   | ✓ Resolved  | Indexer removed                   |
| Subtype overlap                    | ✓ Resolved  | Consolidated on `accounts`        |
| `types` identity collision         | ✓ Resolved  | Categories composite unique       |

### 3.7 Decision log (all v1 open items)

| ID   | v3 resolution                                  |
| ---- | ---------------------------------------------- |
| D-01 | B denormalized; RLS deferred to B3             |
| D-02 | Ledger view canonical; snapshot optional       |
| D-03 | Budgets **deferred**                           |
| D-04 | `/categories` → `categories` table             |
| D-05 | `/movements` → `TRANSFER` transactions         |
| D-06 | Splits **deferred** post-MVP                   |
| D-07 | Global seeds via `owner_id NULL`               |
| D-08 | Tags remain VARCHAR[]                          |
| D-09 | Single `interest_rate` + `interest_rate_basis` |
| D-10 | Migration backfill §5.3                        |

---

## 4. ER diagram (v3)

### 4.1 Mermaid

```mermaid
erDiagram
    users ||--o{ accounts : owns
    users ||--o{ categories : owns
    users ||--o{ transaction_templates : owns
    users ||--o{ transactions : owns
    users ||--o{ account_financing : owns

    accounts ||--o| banking_account_details : extends
    accounts ||--o| real_estate_account_details : extends
    accounts ||--o| trading_account_details : extends
    accounts ||--o| credit_card_account_details : extends
    accounts ||--o| loan_account_details : extends

    accounts ||--o{ account_financing : "asset side"
    accounts ||--o{ account_financing : "loan side"

    categories ||--o{ categories : parent
    categories ||--o{ transaction_templates : classifies
    categories ||--o{ transactions : classifies

    transaction_templates ||--o{ transactions : generates

    accounts ||--o{ transactions : from
    accounts ||--o{ transactions : to

    users {
        uuid id PK
        varchar username
        varchar email
    }

    accounts {
        uuid id PK
        uuid owner_id FK
        enum account_kind
        enum ledger_side
        char currency
        decimal current_value
    }

    categories {
        uuid id PK
        uuid owner_id FK
        uuid parent_id FK
        enum category_kind
        varchar name
    }

    transaction_templates {
        uuid id PK
        uuid owner_id FK
        uuid category_id FK
        decimal planned_amount
    }

    transactions {
        uuid id PK
        uuid owner_id FK
        enum transaction_kind
        decimal amount
        uuid from_account_id FK
        uuid to_account_id FK
        uuid category_id FK
        enum status
    }

    account_financing {
        uuid asset_account_id PK_FK
        uuid loan_account_id PK_FK
        decimal financing_share
    }
```

### 4.2 SVG

Standalone diagram: [`docs/postgres_papita_transactions_v3.svg`](../postgres_papita_transactions_v3.svg)

---

## 5. Alembic migration outline

> **DDL only** — no migration files in this deliverable ([#34](https://github.com/Elmorralito/save-ma-money/issues/34) implements).

### 5.1 Revision plan (single major revision recommended)

| Step | Operation                                   | Notes                                                                                                           |
| ---- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| M-01 | `CREATE TYPE` enums                         | `account_kind`, `ledger_side`, `interest_rate_basis`, `category_kind`, `transaction_kind`, `transaction_status` |
| M-02 | `CREATE TABLE accounts_new`                 | Full v3 `accounts` definition                                                                                   |
| M-03 | `CREATE TABLE` extensions                   | Five 1:1 detail tables                                                                                          |
| M-04 | `CREATE TABLE categories`                   | New taxonomy                                                                                                    |
| M-05 | `CREATE TABLE transaction_templates`        | Rename semantics from `identified_transactions`                                                                 |
| M-06 | `CREATE TABLE transactions_new`             | With CHECK constraints                                                                                          |
| M-07 | `CREATE TABLE account_financing`            | Composite PK                                                                                                    |
| M-08 | Backfill                                    | §5.3 — populate `*_new` tables only                                                                             |
| M-09 | `DROP TABLE` legacy                         | Indexer, types, 10 subtype/template/transaction old tables                                                      |
| M-10 | `ALTER TABLE ... RENAME`                    | `accounts_new` → `accounts`, `transactions_new` → `transactions`                                                |
| M-11 | `CREATE MATERIALIZED VIEW account_balances` | §3.3 — **after** rename so view references final v3 table/column names                                          |
| M-12 | Rebuild indexes + FK graph                  | Verify with ER                                                                                                  |

### 5.2 Upgrade notes

- Run on **empty DB** or **pre-backfill snapshot** only after FR-14 script tested.
- Use single transaction for DDL where Postgres allows; backfill in batched commits.
- `CREATE MATERIALIZED VIEW` only after M-10 rename (M-11); do not create against v0 `transactions` (`value`, no `status`/`currency`).

### 5.3 Backfill mapping (FR-14, D-10)

#### 5.3.1 Legacy `owner_id` (pre-#26 databases)

```sql
-- Seed default user if upgrading legacy dump without users
INSERT INTO papita_transactions.users (id, username, email, password, ...)
VALUES ('00000000-0000-0000-0000-000000000001', 'legacy_migration', 'legacy@local', '...')
ON CONFLICT DO NOTHING;

-- Backfill NULL owner_id before NOT NULL enforcement
UPDATE papita_transactions.accounts SET owner_id = '00000000-0000-0000-0000-000000000001' WHERE owner_id IS NULL;
-- Repeat for all child tables in dependency order
```

Document wipe-and-reload alternative in migration runbook ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)).

#### 5.3.2 `accounts_indexer` → `accounts` + extensions

```
For each accounts_indexer row joined to accounts:
  1. Determine account_kind from populated subtype FKs:
     - banking_asset_account_id → CHECKING (or SAVINGS from type name heuristic)
     - real_estate_asset_account_id → REAL_ESTATE
     - trading_asset_account_id → INVESTMENT_BROKERAGE
     - credit_card_liability_account_id → CREDIT_CARD
     - bank_credit_liability_account_id → LOAN_MORTGAGE
     - asset_account_id only → OTHER_ASSET
     - liability_account_id only → OTHER_LIABILITY
  2. Copy financial columns from assets_accounts OR liability_accounts → accounts
  3. Copy extension columns to matching detail table with account_id = accounts.id
  4. Preserve accounts.id (stable external reference)
```

#### 5.3.3 `types` → `categories`

```sql
INSERT INTO papita_transactions.categories (id, owner_id, name, category_kind, description, tags, ...)
SELECT
    id,
    owner_id,
    name,
    CASE WHEN name ILIKE '%income%' OR name ILIKE '%salary%' THEN 'INCOME' ELSE 'EXPENSE' END,
    description,
    tags,
    ...
FROM papita_transactions.types
WHERE classification = 'TRANSACTIONS';

-- ASSETS/LIABILITIES types: map to account_kind via indexer type_id join; then drop
```

#### 5.3.4 `identified_transactions` → `transaction_templates`

- Map `type_id` → `category_id` using types backfill ID map.
- Rename columns: `planned_value` → `planned_amount`, `planned_transaction_day` → `planned_day`.

#### 5.3.5 Default categories (before transaction backfill)

Seed per-tenant fallback categories so INCOME/EXPENSE rows without a template link satisfy `chk_transaction_kind_accounts`:

```sql
-- One row per (owner_id, category_kind); reuse deterministic UUID from §3.4 hash
INSERT INTO papita_transactions.categories (id, owner_id, name, category_kind, description, tags, ...)
SELECT uuid5(...), u.id, 'Uncategorized Expense', 'EXPENSE', 'Migration default', '{}', ...
FROM papita_transactions.users u
ON CONFLICT DO NOTHING;
-- Mirror for 'Uncategorized Income' / INCOME
```

#### 5.3.6 `transactions` v0 → v3

```sql
-- Income: to_account_id set, from NULL
UPDATE transactions_new t SET
  transaction_kind = 'INCOME',
  category_id = COALESCE(
    (SELECT tt.category_id FROM transaction_templates tt WHERE tt.id = t.template_id),
    (SELECT c.id FROM categories c WHERE c.owner_id = t.owner_id AND c.name = 'Uncategorized Income' AND c.parent_id IS NULL)
  ),
  amount = value, currency = COALESCE(a.currency, 'USD'), status = 'COMPLETED'
FROM accounts_new a
WHERE t.to_account_id = a.id AND t.from_account_id IS NULL;

-- Expense: from set, to NULL — category_id via template or 'Uncategorized Expense' default
-- TRANSFER: both FKs set → transaction_kind = 'TRANSFER', category_id = NULL
```

Reject or quarantine rows where `category_id` would still be NULL after COALESCE (should not occur if §5.3.5 ran).

#### 5.3.7 `financed_asset_accounts` → `account_financing`

v0 FKs point at **subtype row IDs** (`assets_accounts.id`, `bank_credit_liability_accounts.id`), not `accounts.id`. Resolve via indexer:

```sql
INSERT INTO account_financing (asset_account_id, loan_account_id, financing_share, owner_id, ...)
SELECT
  idx_asset.account_id,
  idx_loan.account_id,
  f.financing_share,
  f.owner_id,
  ...
FROM financed_asset_accounts f
JOIN accounts_indexer idx_asset ON idx_asset.asset_account_id = f.asset_account_id
JOIN accounts_indexer idx_loan ON idx_loan.bank_credit_liability_account_id = f.bank_credit_liability_account_id;
```

Validate `financing_share > 0` and owner consistency across both resolved accounts.

#### 5.3.8 Opening balance carry-forward (NF-06)

Ledger-only `account_balances` will read `0` for accounts with snapshot values but sparse transaction history. After M-08 transaction backfill, synthesize **opening-balance** rows where `initial_value` / migrated `current_value` ≠ ledger sum:

```sql
-- For each account where ledger balance != accounts.initial_value (or current_value for illiquid kinds):
INSERT INTO transactions_new (transaction_kind, amount, currency, to_account_id, category_id, description, status, ...)
VALUES ('INCOME', <delta>, <currency>, <account_id>, <uncategorized_income_id>, 'Opening balance (migration)', 'COMPLETED', ...);
-- Use EXPENSE/from_account_id for negative deltas on liability accounts
```

Document tolerance and manual review queue for accounts where snapshot vs ledger cannot be reconciled automatically.

### 5.4 Downgrade outline

1. Recreate v0 tables (14-table DDL from v0 audit §3).
2. Reverse-map v3 → v0 (lossy: `account_kind` → indexer FKs; TRANSFER → two expense/income rows optional).
3. Drop v3 enums, view, tables.
4. **Downgrade is best-effort** — document data loss for `categories.parent_id`, `transaction_kind`, currency columns.

---

## 6. Intentional denormalizations

| Denormalization                                  | Table(s)            | Rationale                                                                                           | Reconciliation                                                                     |
| ------------------------------------------------ | ------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `transactions.owner_id`                          | `transactions`      | Tenant-scoped ledger scans without joining `accounts` on every list/report query (FR-02 strategy B) | CHECK `chk_transaction_owner_accounts`; service upsert sets from account           |
| `account_financing.owner_id`                     | `account_financing` | Avoid 3-way join for tenant filter on financing relationships                                       | CHECK matches asset + loan account owners                                          |
| `accounts.current_value` + `current_value_as_of` | `accounts`          | Illiquid assets (real estate) where ledger does not capture mark-to-market (NF-06)                  | Nightly reconciliation job vs `account_balances`; API labels snapshot with `as_of` |
| Global `categories` seeds (`owner_id NULL`)      | `categories`        | Shared default taxonomy for new users without per-register copy (FR-15)                             | Global rows read-only; tenant writes always set `owner_id`                         |
| `tags` VARCHAR[]                                 | multiple            | Query simplicity for ingestion pipeline; acceptable 1NF multi-value (v0 §4.1)                       | GIN index optional if tag search needed                                            |

**No other 3NF exceptions** without documented rationale.

---

## 7. Sign-off checklist (G1)

Maintainer approval required on [#28](https://github.com/Elmorralito/save-ma-money/issues/28) before [#25](https://github.com/Elmorralito/save-ma-money/issues/25) CRUD begins.

| #   | Item                                                            | Confirm |
| --- | --------------------------------------------------------------- | ------- |
| 1   | `accounts_indexer` elimination acceptable                       | ☐       |
| 2   | Tenancy: denormalized `owner_id` on hot tables (B), RLS later   | ☐       |
| 3   | Budgets deferred from MVP (FR-09)                               | ☐       |
| 4   | `/movements` as TRANSFER alias, no `movements` table            | ☐       |
| 5   | Categories hierarchy + `category_kind` replaces `types` for API | ☐       |
| 6   | `account_balances` materialized view as balance source          | ☐       |
| 7   | Transaction CHECK constraints (INCOME/EXPENSE/TRANSFER)         | ☐       |
| 8   | `account_financing` composite PK + owner CHECKs                 | ☐       |
| 9   | Legacy backfill approach (seed user vs wipe-and-reload)         | ☐       |
| 10  | Intentional denormalizations §6 accepted                        | ☐       |

**Suggested sign-off comment template:**

> G1 — v3 schema approved. Tenancy: B. Budgets: deferred. Movements: TRANSFER alias. Proceed to #33 API mapping and #34 migrations.

---

## 8. Issue #32 comment draft

```markdown
## PPT-031-B deliverable: v1–v3 target schema

Track A Steps A2–A4 delivered in:

- [`docs/design/PPT-031-v1-schema.md`](docs/design/PPT-031-v1-schema.md) — v1 draft, v2 API review, v3 freeze
- [`docs/postgres_papita_transactions_v3.svg`](docs/postgres_papita_transactions_v3.svg) — ER diagram

### Summary

| Version | Key outcome                                                                              |
| ------- | ---------------------------------------------------------------------------------------- |
| v1      | Eliminate `accounts_indexer`; consolidate accounts + 1:1 extensions; tenancy options     |
| v2      | `/categories` → `categories`; `/movements` → TRANSFER transactions; budgets **deferred** |
| v3      | 11 tables + `account_balances` view; CHECK constraints; Alembic outline §5               |

### Requirements addressed

FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-09 (defer), FR-14 (outline), FR-15, FR-16

### Next step

**G1:** Maintainer sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28) using §7 checklist — blocks [#25](https://github.com/Elmorralito/save-ma-money/issues/25) CRUD.
```

---

## References

- v0 audit: [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md)
- Parent: [#28](https://github.com/Elmorralito/save-ma-money/issues/28)
- API spec: [`modules/api/API_Endpoints.md.md`](../../modules/api/API_Endpoints.md.md)
- v0 ER: referenced in v0 audit §2.2 (predates `users`; PNG not committed in repo — regenerate from v0 schema if needed)
- v4 extensions: [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) — post-MVP additive schema (budgets, splits, reconciliation, …)
