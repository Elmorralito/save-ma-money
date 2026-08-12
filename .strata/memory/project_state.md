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

- **PPT-080 / #174:** `GmailSource` + `GmailSettings` on main (#214).
- **PPT-079 / #173:** core contracts, registries, `IngestionRunner` on main (#213).
- **PPT-078 / #172:** provenance sidecar + `IngestionBridgeService` on main (#212).
- **PPT-077 / #171:** ingestor-core + email package scaffolds on main (#211).

### In progress (ACTIVE)

- **PPT-081 / #175:** Bancolombia + synthetic Nequi email parsers + hybrid
  `FallbackEmailParser` on `175-featppt-081-…` (R1=B; COP; FKs deferred to #176).
  Parent epic **PPT-076 / #170**. Downstream hard: #176 Prefect/end-to-end.

### Open (backlog)

- **PPT-076** remaining children after #175 (email flow #176, etc.).
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.
- Alembic/`alembic check` SQLModel CHECK alignment (`chk_financing_share`, etc.).

### Next action

- Land PPT-081 / #175; hand off stable `parser_id`s + unrecognized→DLQ semantics to
  PPT-082 / #176 (account/category FK resolution). Do not ship Nu under `NequiParser`.

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
