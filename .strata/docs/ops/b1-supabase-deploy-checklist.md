# Ops pointer — B1 Supabase (PPT-039)

Human-facing staging/prod checklist (secrets names, URL split, smoke, #50 handoff):

[`docs/ops/b1-supabase-deploy-checklist.md`](../../../docs/ops/b1-supabase-deploy-checklist.md)

Pooler modes: [`docs/issues/PPT-031-C-supabase-decision-brief.md`](../../../docs/issues/PPT-031-C-supabase-decision-brief.md) §2.2.

Migrations: `./deploy/alembic.sh upgrade --url "$DATABASE_URL_MIGRATIONS"` (direct `:5432` only).
