---
trigger: before adding ingest uniqueness or ledger upsert conflict keys
applies-when: modules/model/**/ingestion*, modules/model/**/upsert.py, modules/model/alembic/**
origin: success
---

**Lesson:** Do not put `(owner_id, ingestion_source, source_ref)` uniqueness on partitioned
`transactions` (PK is `(id, transaction_ts)`). Use a non-partitioned provenance sidecar with
composite FK to `(id, transaction_ts)`, partial unique `WHERE source_ref IS NOT NULL`, and
sidecar-first re-ingest that reuses id/`transaction_ts` and reactivates soft-deleted rows.
Extend `PostgreSQLUpserter` with `conflict_index_elements` / `conflict_index_where` /
`immutable_update_columns` when bulk conflict targets are not the PK. For `alembic check`,
`include_object` must ignore FKs reflected onto monthly `transactions_y*m*` partitions and
known DB-only CHECKs (`chk_transaction_kind_accounts`, etc.).
