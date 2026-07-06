# PPT-031 v4: Post-MVP Schema Extensions

| Field            | Value                                                                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Parent**       | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) · builds on [v3 freeze](PPT-031-v1-schema.md#3-v3-frozen-target-schema)                           |
| **Prerequisite** | G1 sign-off on v3 ([#32](https://github.com/Elmorralito/save-ma-money/issues/32))                                                                               |
| **Platform**     | PostgreSQL via Supabase                                                                                                                                         |
| **Date**         | 2026-07-06                                                                                                                                                      |
| **Status**       | Proposed — **does not modify v3 G1 scope**; ships as Alembic revision series after v3 migration ([#34](https://github.com/Elmorralito/save-ma-money/issues/34)) |

---

## 1. Purpose

v3 intentionally deferred several API-spec features and domain patterns. This document **freezes the v4 additive schema** so [#33](https://github.com/Elmorralito/save-ma-money/issues/33) and [#25](https://github.com/Elmorralito/save-ma-money/issues/25) can plan a second implementation wave without reopening v3 structural decisions.

**In scope:** budgets, splits, recurrence, credit-card cycles, reconciliation, counterparties, categorization rules, attachments, import tracking, supplemental read models, RLS policy outline.

**Explicitly out of scope (do not add):**

| Avoid                                                     | Reason                                                                                                   |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Double-entry `journal_entries` / `journal_lines`          | v3 `transaction_kind` ledger is sufficient for personal finance; adds join cost without MVP benefit      |
| Additional account subtype tables                         | v3 `account_kind` + 1:1 extensions is the consolidation endpoint (FR-04)                                 |
| `transactions.metadata` / `accounts.metadata` JSONB blobs | Opaque, unqueryable; use structured tables (`transaction_attachments`, typed columns)                    |
| Duplicate balance columns on `accounts`                   | Ledger + materialized views remain canonical (§3.5 v3); never add `stored_balance`                       |
| `holdings` / securities master                            | Brokerage remains `trading_account_details` + `current_value` until investment scope is a dedicated epic |
| DuckDB dialect branches                                   | PostgreSQL / Supabase only                                                                               |

---

## 2. Release phasing

| Phase    | Tables / views                                                                                           | Unblocks                                                                                  |
| -------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **v4.1** | `budgets`, `budget_allocations`, `transaction_splits`, `category_spending_monthly` view                  | `/budgets/*`, split endpoint, `budget-performance` report                                 |
| **v4.2** | Template recurrence columns, `credit_card_account_details` cycle fields                                  | NF-17, credit-card lifecycle                                                              |
| **v4.3** | `counterparties`, `categorization_rules`                                                                 | Auto-categorization, merchant reports                                                     |
| **v4.4** | `transaction_events`, `account_reconciliations`, `reconciliation_items`, `cleared_account_balances` view | Movement execute audit, bank reconciliation                                               |
| **v4.5** | `transaction_attachments`, `import_batches`, `import_batch_errors`                                       | Receipts, registrar idempotency (FR-08)                                                   |
| **v4.6** | `tags`, `entity_tags`, `net_worth_snapshots` view                                                        | Cross-entity tag search, dashboard snapshots                                              |
| **v4.7** | RLS policies (B3) on tenant tables                                                                       | Supabase defense-in-depth ([#31](https://github.com/Elmorralito/save-ma-money/issues/31)) |

Phases may ship as one or more Alembic revisions each; order respects FK dependencies.

---

## 3. Entity overview

```
v3 core (unchanged)
  └── v4 additions
        budgets ── budget_allocations ── categories
        transactions ── transaction_splits
        transactions ── transaction_events
        transactions ── transaction_attachments
        transactions ── counterparties (optional FK)
        transaction_templates (+ recurrence columns)
        credit_card_account_details (+ cycle columns)
        accounts ── account_reconciliations ── reconciliation_items ── transactions
        categorization_rules ── categories, counterparties
        import_batches ── import_batch_errors
        tags ── entity_tags (polymorphic)
        views: category_spending_monthly, cleared_account_balances, net_worth_snapshots
```

ER diagram: [`docs/postgres_papita_transactions_v4.svg`](../postgres_papita_transactions_v4.svg)

---

## 4. Table definitions

All tables extend `BaseSQLModel` unless noted. All tenant-scoped tables carry `owner_id NOT NULL` unless stated.

### 4.1 `budgets` (FR-09)

| Column         | Type          | Notes                                        |
| -------------- | ------------- | -------------------------------------------- |
| `id`           | UUID          | PK                                           |
| `owner_id`     | UUID          | FK → `users.id`                              |
| `name`         | VARCHAR(255)  | NOT NULL                                     |
| `period`       | ENUM          | `MONTHLY` \| `YEARLY` \| `CUSTOM`            |
| `start_date`   | DATE          | NOT NULL                                     |
| `end_date`     | DATE          | NOT NULL                                     |
| `total_amount` | DECIMAL(22,8) | NOT NULL, `gt=0`                             |
| `currency`     | CHAR(3)       | NOT NULL, matches tenant default or explicit |
| `status`       | ENUM          | `DRAFT` \| `ACTIVE` \| `CLOSED`              |
| audit columns  | —             | BaseSQLModel                                 |

**CHECK:** `start_date <= end_date`

**Indexes:** `(owner_id, status)`, `(owner_id, start_date, end_date)`

**API mapping:** `/budgets/*`; `spent_amount` / `remaining_amount` are **computed** (not stored) from allocations + ledger.

### 4.2 `budget_allocations`

| Column             | Type          | Notes                |
| ------------------ | ------------- | -------------------- |
| `id`               | UUID          | PK                   |
| `owner_id`         | UUID          | FK → `users.id`      |
| `budget_id`        | UUID          | FK → `budgets.id`    |
| `category_id`      | UUID          | FK → `categories.id` |
| `allocated_amount` | DECIMAL(22,8) | NOT NULL, `ge=0`     |
| audit columns      | —             | BaseSQLModel         |

**Unique:** `UNIQUE (budget_id, category_id)`

**Spent computation (FR-12):**

```sql
SELECT ba.*,
       COALESCE(SUM(t.amount) FILTER (
         WHERE t.transaction_kind = 'EXPENSE'
           AND t.category_id = ba.category_id
           AND t.transaction_ts BETWEEN b.start_date AND b.end_date
           AND t.status = 'COMPLETED'
       ), 0) AS spent_amount
FROM budget_allocations ba
JOIN budgets b ON b.id = ba.budget_id
LEFT JOIN transactions t ON t.owner_id = ba.owner_id
GROUP BY ba.id, b.start_date, b.end_date;
```

### 4.3 `transaction_splits`

| Column           | Type          | Notes                  |
| ---------------- | ------------- | ---------------------- |
| `id`             | UUID          | PK                     |
| `owner_id`       | UUID          | FK → `users.id`        |
| `transaction_id` | UUID          | FK → `transactions.id` |
| `category_id`    | UUID          | FK → `categories.id`   |
| `amount`         | DECIMAL(22,8) | NOT NULL, `gt=0`       |
| `description`    | TEXT          | default `''`           |
| audit columns    | —             | BaseSQLModel           |

**Service rule:** `SUM(split.amount) = parent.amount` (tolerance ±0.01); parent `category_id` becomes NULL or "split parent" sentinel when splits exist.

**API mapping:** `POST /transactions/{id}/split`

### 4.4 `transaction_templates` — recurrence columns (ALTER v3 table)

| Column                | Type         | Notes                                                |
| --------------------- | ------------ | ---------------------------------------------------- |
| `recurrence_rule`     | VARCHAR(512) | NULL; iCal RRULE (e.g. `FREQ=MONTHLY;BYMONTHDAY=15`) |
| `recurrence_timezone` | VARCHAR(64)  | NULL; IANA tz for rule evaluation                    |
| `recurrence_end_date` | DATE         | NULL                                                 |

**Fallback:** when `recurrence_rule IS NULL`, use existing `planned_day` / `use_month_end` (v3).

**Resolves:** NF-17 (days 29–31, month-end) without a separate `recurrence_schedules` table.

### 4.5 `credit_card_account_details` — cycle columns (ALTER v3 table)

| Column                | Type          | Notes        |
| --------------------- | ------------- | ------------ |
| `statement_close_day` | SMALLINT      | 1–31         |
| `payment_due_day`     | SMALLINT      | 1–31         |
| `apr`                 | DECIMAL(10,6) | NULL         |
| `minimum_payment`     | DECIMAL(22,8) | NULL, `ge=0` |

**No new table** — extends existing 1:1 extension only.

### 4.6 `counterparties`

| Column                | Type         | Notes                                 |
| --------------------- | ------------ | ------------------------------------- |
| `id`                  | UUID         | PK                                    |
| `owner_id`            | UUID         | FK → `users.id`                       |
| `name`                | VARCHAR(255) | NOT NULL                              |
| `normalized_name`     | VARCHAR(255) | NOT NULL; lower(trim(name)) for dedup |
| `default_category_id` | UUID         | NULL, FK → `categories.id`            |
| `tags`                | VARCHAR[]    | default `{}`                          |
| audit columns         | —            | BaseSQLModel                          |

**Unique:** `UNIQUE (owner_id, normalized_name)`

### 4.7 `transactions` — additive FK (ALTER v3 table)

| Column            | Type | Notes                          |
| ----------------- | ---- | ------------------------------ |
| `counterparty_id` | UUID | NULL, FK → `counterparties.id` |
| `budget_id`       | UUID | NULL, FK → `budgets.id`        |

**Optional FKs** — NULL for legacy rows. `budget_id` set when user assigns transaction to active budget period.

### 4.8 `categorization_rules`

| Column             | Type          | Notes                                                                             |
| ------------------ | ------------- | --------------------------------------------------------------------------------- |
| `id`               | UUID          | PK                                                                                |
| `owner_id`         | UUID          | FK → `users.id`                                                                   |
| `priority`         | SMALLINT      | NOT NULL default 100; lower = higher precedence                                   |
| `match_type`       | ENUM          | `DESCRIPTION_CONTAINS` \| `DESCRIPTION_REGEX` \| `COUNTERPARTY` \| `AMOUNT_RANGE` |
| `match_value`      | VARCHAR(512)  | Pattern or counterparty_id (UUID string when type=COUNTERPARTY)                   |
| `match_amount_min` | DECIMAL(22,8) | NULL                                                                              |
| `match_amount_max` | DECIMAL(22,8) | NULL                                                                              |
| `category_id`      | UUID          | FK → `categories.id`                                                              |
| `is_active`        | BOOLEAN       | default true (separate from soft delete)                                          |
| audit columns      | —             | BaseSQLModel                                                                      |

**Evaluation:** on transaction create/import, apply rules ordered by `priority`; first match wins; skip if `category_id` already set.

### 4.9 `transaction_events`

| Column           | Type         | Notes                                          |
| ---------------- | ------------ | ---------------------------------------------- |
| `id`             | UUID         | PK                                             |
| `owner_id`       | UUID         | FK → `users.id`                                |
| `transaction_id` | UUID         | FK → `transactions.id`                         |
| `from_status`    | ENUM         | NULL for initial create                        |
| `to_status`      | ENUM         | `PENDING` \| `COMPLETED` \| `CANCELLED`        |
| `event_ts`       | TIMESTAMP    | NOT NULL default now()                         |
| `actor`          | VARCHAR(128) | `system` \| `user:{id}` \| `import:{batch_id}` |
| `note`           | TEXT         | default `''`                                   |

**Append-only** — no updates/deletes except soft-delete cascade.

**API mapping:** `POST /movements/{id}/execute` inserts `PENDING → COMPLETED` event.

### 4.10 `account_reconciliations`

| Column               | Type          | Notes                                       |
| -------------------- | ------------- | ------------------------------------------- |
| `id`                 | UUID          | PK                                          |
| `owner_id`           | UUID          | FK → `users.id`                             |
| `account_id`         | UUID          | FK → `accounts.id`                          |
| `statement_end_date` | DATE          | NOT NULL                                    |
| `statement_balance`  | DECIMAL(22,8) | NOT NULL                                    |
| `status`             | ENUM          | `IN_PROGRESS` \| `COMPLETED` \| `ABANDONED` |
| `completed_at`       | TIMESTAMP     | NULL                                        |
| audit columns        | —             | BaseSQLModel                                |

### 4.11 `reconciliation_items`

| Column              | Type      | Notes                             |
| ------------------- | --------- | --------------------------------- |
| `id`                | UUID      | PK                                |
| `owner_id`          | UUID      | FK → `users.id`                   |
| `reconciliation_id` | UUID      | FK → `account_reconciliations.id` |
| `transaction_id`    | UUID      | FK → `transactions.id`            |
| `cleared_at`        | TIMESTAMP | NOT NULL                          |
| audit columns       | —         | BaseSQLModel                      |

**Unique:** `UNIQUE (reconciliation_id, transaction_id)`

**Distinction:** ledger balance (all `COMPLETED` transactions) vs **cleared balance** (items linked to latest completed reconciliation).

### 4.12 `transaction_attachments`

| Column            | Type         | Notes                       |
| ----------------- | ------------ | --------------------------- |
| `id`              | UUID         | PK                          |
| `owner_id`        | UUID         | FK → `users.id`             |
| `transaction_id`  | UUID         | FK → `transactions.id`      |
| `storage_key`     | VARCHAR(512) | NOT NULL; object store path |
| `filename`        | VARCHAR(255) | NOT NULL                    |
| `mime_type`       | VARCHAR(128) | NOT NULL                    |
| `byte_size`       | BIGINT       | NOT NULL, `ge=0`            |
| `checksum_sha256` | CHAR(64)     | NULL                        |
| audit columns     | —            | BaseSQLModel                |

**No JSONB** — structured metadata only; binary in object storage (Supabase Storage).

### 4.13 `import_batches` (FR-08)

| Column               | Type         | Notes                                             |
| -------------------- | ------------ | ------------------------------------------------- |
| `id`                 | UUID         | PK                                                |
| `owner_id`           | UUID         | FK → `users.id`                                   |
| `source`             | VARCHAR(128) | e.g. `registrar:csv`, `api:bulk`                  |
| `source_fingerprint` | VARCHAR(64)  | SHA256 of input for idempotency                   |
| `status`             | ENUM         | `RUNNING` \| `SUCCEEDED` \| `PARTIAL` \| `FAILED` |
| `rows_total`         | INTEGER      | default 0                                         |
| `rows_inserted`      | INTEGER      | default 0                                         |
| `rows_updated`       | INTEGER      | default 0                                         |
| `rows_failed`        | INTEGER      | default 0                                         |
| `started_at`         | TIMESTAMP    | NOT NULL                                          |
| `finished_at`        | TIMESTAMP    | NULL                                              |
| audit columns        | —            | BaseSQLModel                                      |

**Unique:** `UNIQUE (owner_id, source, source_fingerprint)` — reject duplicate loads.

### 4.14 `import_batch_errors`

| Column            | Type        | Notes                                  |
| ----------------- | ----------- | -------------------------------------- |
| `id`              | UUID        | PK                                     |
| `owner_id`        | UUID        | FK → `users.id`                        |
| `import_batch_id` | UUID        | FK → `import_batches.id`               |
| `row_number`      | INTEGER     | NULL                                   |
| `error_code`      | VARCHAR(64) | NOT NULL                               |
| `error_message`   | TEXT        | NOT NULL                               |
| `raw_payload`     | TEXT        | NULL; truncated row JSON for debugging |
| `created_at`      | TIMESTAMP   | NOT NULL                               |

### 4.15 `tags` + `entity_tags` (optional v4.6)

Normalized tag search without replacing existing `tags VARCHAR[]` on v3 tables (additive).

**`tags`:** `id` PK, `owner_id` FK, `name` VARCHAR(64), UNIQUE `(owner_id, name)`

**`entity_tags`:** `tag_id` FK, `entity_type` ENUM (`ACCOUNT` \| `TRANSACTION` \| `CATEGORY` \| `COUNTERPARTY`), `entity_id` UUID, UNIQUE `(tag_id, entity_type, entity_id)`

Ingestion may dual-write ARRAY + junction during transition.

---

## 5. Read models (materialized views)

All refresh via scheduled job or post-batch `REFRESH MATERIALIZED VIEW CONCURRENTLY` — **never** stored as duplicate columns on base tables.

### 5.1 `category_spending_monthly` (v4.1)

```sql
CREATE MATERIALIZED VIEW papita_transactions.category_spending_monthly AS
SELECT
    t.owner_id,
    date_trunc('month', t.transaction_ts)::date AS month,
    COALESCE(s.category_id, t.category_id) AS category_id,
    t.currency,
    SUM(COALESCE(s.amount, t.amount)) AS total_spent
FROM papita_transactions.transactions t
LEFT JOIN papita_transactions.transaction_splits s ON s.transaction_id = t.id
WHERE t.transaction_kind = 'EXPENSE'
  AND t.status = 'COMPLETED'
  AND t.active = true
GROUP BY 1, 2, 3, 4;
```

### 5.2 `cleared_account_balances` (v4.4)

Balance of transactions cleared in the latest completed reconciliation per account.

### 5.3 `net_worth_snapshots` (v4.6)

```sql
-- Monthly rollup: sum(asset ledger balances) - sum(liability ledger balances) per owner
-- Uses account_balances (v3) joined to accounts.ledger_side
```

Illiquid `current_value` overrides merged in service layer for REAL_ESTATE kinds only (not stored in view).

---

## 6. RLS policy outline (v4.7 — B3)

Deferred from v3; apply after app-layer tenancy is stable.

```sql
ALTER TABLE papita_transactions.transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY transactions_tenant_isolation ON papita_transactions.transactions
  USING (owner_id = current_setting('app.user_id', true)::uuid);
-- Repeat for: accounts, categories, budgets, budget_allocations,
-- transaction_splits, counterparties, categorization_rules,
-- account_reconciliations, reconciliation_items, transaction_attachments,
-- import_batches, tags
```

**Service contract:** API sets `SET LOCAL app.user_id = :current_user` per request via SQLAlchemy `connection.execute()` before queries. RLS is **additive** to `OwnedTableRepository` filters, not a replacement.

---

## 7. Alembic outline (v4 revision series)

| Step  | Operation                                                                          |
| ----- | ---------------------------------------------------------------------------------- |
| V4-01 | `CREATE TYPE` for new enums                                                        |
| V4-02 | `budgets`, `budget_allocations`                                                    |
| V4-03 | `transaction_splits`; `category_spending_monthly` view                             |
| V4-04 | `ALTER transaction_templates` recurrence columns                                   |
| V4-05 | `ALTER credit_card_account_details` cycle columns                                  |
| V4-06 | `counterparties`; `ALTER transactions` add `counterparty_id`, `budget_id`          |
| V4-07 | `categorization_rules`                                                             |
| V4-08 | `transaction_events`                                                               |
| V4-09 | `account_reconciliations`, `reconciliation_items`; `cleared_account_balances` view |
| V4-10 | `transaction_attachments`                                                          |
| V4-11 | `import_batches`, `import_batch_errors`                                            |
| V4-12 | `tags`, `entity_tags`; `net_worth_snapshots` view                                  |
| V4-13 | RLS policies (optional flag; Supabase staging only until tested)                   |

Each revision: PostgreSQL DDL + downgrade notes per NFR-01.

---

## 8. API coverage after v4

| API area                        | v3          | v4                     |
| ------------------------------- | ----------- | ---------------------- |
| `/budgets/*`                    | Deferred    | ✓                      |
| `/transactions/{id}/split`      | Deferred    | ✓                      |
| `transactions.budget_id`        | Removed     | ✓ restored             |
| `transactions.attachments`      | Deferred    | ✓                      |
| `transactions.recurrence_rule`  | Deferred    | ✓                      |
| `/reports/budget-performance`   | Deferred    | ✓                      |
| `/movements/{id}/execute` audit | status only | ✓ `transaction_events` |

---

## 9. 3NF and denormalization notes

| Choice                               | Rationale                                                                                     |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| No stored `spent_amount` on budgets  | Derived from ledger — avoids update anomalies                                                 |
| `transactions.budget_id` nullable FK | Convenience filter; derivable from date + category + allocations — documented denormalization |
| `counterparties.normalized_name`     | Dedup aid; `name` is display truth                                                            |
| Keep `tags VARCHAR[]` on v3 entities | Do not migrate away in v4; junction is additive                                               |
| No JSONB metadata                    | Structured tables preserve queryability and validation                                        |

---

## 10. Sign-off checklist (G4 extension)

| #   | Item                                                                                                    | Confirm |
| --- | ------------------------------------------------------------------------------------------------------- | ------- |
| 1   | Budgets ship as v4.1, not retrofitted into v3 G1                                                        | ☐       |
| 2   | Splits sum validation in service layer                                                                  | ☐       |
| 3   | Recurrence via RRULE on templates (no separate schedule table)                                          | ☐       |
| 4   | Reconciliation cleared vs ledger balance distinction accepted                                           | ☐       |
| 5   | Attachments in object storage, DB holds metadata only                                                   | ☐       |
| 6   | Double-entry journal explicitly rejected                                                                | ☐       |
| 7   | RLS (v4.7) optional until B3 confirmed on [#31](https://github.com/Elmorralito/save-ma-money/issues/31) | ☐       |

---

## References

- v3 freeze: [`PPT-031-v1-schema.md`](PPT-031-v1-schema.md)
- v0 audit gaps: [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md) §4.5, §14
- API spec: [`modules/api/API_Endpoints.md.md`](../../modules/api/API_Endpoints.md.md)
- ER (v4): [`docs/postgres_papita_transactions_v4.svg`](../postgres_papita_transactions_v4.svg)
