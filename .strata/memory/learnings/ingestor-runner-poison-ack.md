---
trigger: before changing IngestionRunner ack / DLQ / dry_run semantics
applies-when: modules/ingestor-core/**/runner/**, modules/ingestor-core/**/mapping/**
origin: success
---

**Lesson:** On parse/validation failure, write DLQ then **ack** (poison-message) so sources do not redeliver forever into unbounded DLQ rows. Persist failures must **not** ack. Require non-empty `source_ref` for bridge idempotency. Honor `dry_run` / `fetch_limit` in the runner, not only in settings subclasses.
