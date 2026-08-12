---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

**Strata issues policy:** do **not** keep closed GitHub issues under `.strata/issues/`
(including `archive/`) — they add agent context noise. History lives on GitHub / git.
Capture with `/strata:capture` only for work in flight.

### Last completed (this session)

- **PPT-081 / #175:** Bancolombia + synthetic Nequi parsers + Fallback on main.
- **PPT-080 / #174:** `GmailSource` + `GmailSettings` on main (#214).
- **PPT-079 / #173:** core contracts, registries, `IngestionRunner` on main (#213).
- **PPT-078 / #172:** provenance sidecar + `IngestionBridgeService` on main (#212).
- **PPT-077 / #171:** ingestor-core + email package scaffolds on main (#211).

### In progress (ACTIVE)

- **PPT-082 / #176:** Prefect hourly email flow + Compose packaging on
  `176-featppt-082-…`. Defaults locked: H1=B (no live FK enricher; tests inject
  FKs / assert DLQ), H2=`PAPITA_INGESTOR_OWNER_ID`, H3=AC3 DLQ-then-ack.
  Parent epic **PPT-076 / #170**. Downstream: #177 API run-status, #178 e2e.

### Open (backlog)

- **PPT-076** remaining: #177 API connection/run-status, #178 e2e/tests/docs.
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.
- Alembic/`alembic check` SQLModel CHECK alignment (`chk_financing_share`, etc.).

### Next action

- Commit/PR PPT-082; hand off flow name `papita-email-ingestion` /
  `papita-email-ingestion-hourly` to PPT-083 / #177. Live account/category FK
  enricher remains deferred (H1=B).
