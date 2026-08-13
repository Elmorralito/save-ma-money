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

- **PPT-082 / #176:** Prefect hourly email flow + Compose packaging on main (#216).
- **PPT-081 / #175:** Bancolombia + synthetic Nequi parsers + Fallback on main.
- **PPT-080 / #174:** `GmailSource` + `GmailSettings` on main (#214).
- **PPT-079 / #173:** core contracts, registries, `IngestionRunner` on main (#213).
- **PPT-078 / #172:** provenance sidecar + `IngestionBridgeService` on main (#212).

### In progress (ACTIVE)

- **PPT-083 / #177:** ingestion connection + run-status — model tables/Alembic,
  email worker persist hook (`RunResult` mapped at plugin boundary), read-only
  `GET /api/v1/ingestion/*` (401 / cross-tenant 404; no HTTP run trigger).
  Soft-delete connection upsert reactivates natural key; serve `deployment_name`
  wired into deps. Branch `177-featppt-083-…`. Parent epic **PPT-076 / #170**.

### Open (backlog)

- **PPT-076** remaining: #178 e2e/tests/docs (OpenAPI web regen / packaging gate).
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.
- Alembic/`alembic check` SQLModel CHECK alignment (`chk_financing_share`, etc.).

### Next action

- Ship PPT-083 PR; apply model migration on B0 (`l9a0b1c2d3e4`). Full OpenAPI/CI
  web contract refresh deferred to PPT-084 / #178. Live FK enricher still H1=B.
