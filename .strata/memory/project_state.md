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

- **PPT-078 / #172:** provenance sidecar + `IngestionBridgeService` on main (#212).
- **PPT-077 / #171:** ingestor-core + email package scaffolds on main (#211).
- **PPT-070 / #163:** epic closed — payment dues #164–#168
  (PRs [#197](https://github.com/Elmorralito/save-ma-money/pull/197)–[#207](https://github.com/Elmorralito/save-ma-money/pull/207)).

### In progress (ACTIVE)

- **PPT-079 / #173:** core contracts, registries, `IngestionRunner` on `feat/PPT-079`
  (persist-then-ack; DLQ-then-ack poison semantics; `source_ref` required).
  Parent epic **PPT-076 / #170**. Downstream: #174 / #175 / #176.

### Open (backlog)

- **PPT-076** remaining children after #173 (Gmail source, bank parsers, email flow, etc.).
- **PPT-066 follow-up:** after 1–2 releases, drop legacy `model-v*` publish trigger.
- Alembic/`alembic check` SQLModel CHECK alignment (`chk_financing_share`, etc.).

### Next action

- Land PPT-079 / #173 ([PR #213](https://github.com/Elmorralito/save-ma-money/pull/213));
  keep plugins consuming contracts (do not redefine them).
  QC note: prettier blank-line fix in `modules/model/CHANGELOG.md` for `--all-files`.

### Uncommitted / staging notes

- Do not commit `environments/**/.env` or `modules/web` secrets (`VITE_*` public only)
- `modules/**` changes need a paired `.strata/` touch (strict mode)
- PSR → `modules/model/CHANGELOG.md` only; root CHANGELOG = auto-updates.yml
