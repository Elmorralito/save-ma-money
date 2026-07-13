---
name: save-ma-money State
description: PPT-039 repurposed to Supabase Auth; epic #42 Auth-first (pooler optional).
---

## WHERE WE LEFT OFF (current)

**Session — 2026-07-13.** Executed Auth-first strategy: #49/#42 reissue docs,
PPT-031-C G7 supersede, README/AGENTS/environments aligned. Next: implement Supabase
JWT verify in API (PPT-039 code).

### Last completed (this session)

- `docs/issues/PPT-039-supabase-auth-reissue.md` + GH body drafts
- Brief G7 supersede; epic/API docs no longer require Supabase PG
- Pooler work marked optional ops

### Next action

- Publish `gh issue edit` for #49 / #42 if not yet applied
- Implement Auth: JWKS verify, `get_current_owner` provision, env `SUPABASE_URL`
- Update #50 secret contract

### Prerequisites

- `export PAPITA_ENV=local`
- Supabase project for Auth (not necessarily for Postgres)

### Uncommitted / staging notes

- Stage `.strata/` with docs/`modules`/`environments` changes
- Do not commit `environments/**/.env`
