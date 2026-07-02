# PPT-031-C: Supabase × FastAPI integration decision record

**GitHub issue:** [#31](https://github.com/Elmorralito/save-ma-money/issues/31) · **Parent:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) · **Track:** B

## Document ↔ issue cross-reference

| Related document | Issue |
|------------------|-------|
| [`PPT-031-simplify-requirements.md`](./PPT-031-simplify-requirements.md) | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — requirements (Track B) |
| [`../design/PPT-031-v0-audit.md`](../design/PPT-031-v0-audit.md) | [#30](https://github.com/Elmorralito/save-ma-money/issues/30) — audit §11 auth |
| `../design/PPT-031-migration-runbook.md` *(planned)* | [#34](https://github.com/Elmorralito/save-ma-money/issues/34) — RLS migrations (B3) |
| `../design/PPT-031-auth-contract.md` *(planned)* | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) Track E — FR-10/11 |

---

## Platform decision (2026-07-02)

**DuckDB is out of scope.** The sole supported database platform for PPT-031 is **PostgreSQL via Supabase** (Docker Postgres acceptable for local Alembic runs). See [#34](https://github.com/Elmorralito/save-ma-money/issues/34).

---

## Goal

Document Supabase × FastAPI integration and produce a decision record for auth/RLS options — **not full implementation** until v3 schema is frozen ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)).

---

## Options matrix

| Option | Description | When to choose |
|--------|-------------|----------------|
| **B0 — Local Postgres** | Docker Postgres locally; Supabase for staging/prod | Default for dev teams wanting offline local DB |
| **B1 — Supabase Postgres everywhere** | All envs use Supabase pooler `DATABASE_URL` | Simplest ops; no local Docker required |
| **B2 — Supabase Auth** | OAuth/magic links via Supabase; app schema unchanged | When delegating auth to Supabase |
| **B3 — Supabase Auth + RLS** | B2 + Row Level Security on `owner_id` | Strongest tenant isolation at DB layer |

~~Former option: Self-hosted Postgres + DuckDB~~ — **removed**. Do not document or evaluate DuckDB paths.

---

## Deliverables

- [ ] Decision record: chosen B0–B3 with pros/cons
- [ ] `DATABASE_URL` format for Supabase pooler (transaction vs session mode)
- [ ] Env var documentation: `DATABASE_URL`, `JWT_SECRET_KEY`, optional `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (NFR-05)
- [ ] FastAPI integration notes: session DI via `SQLDatabaseConnector`, health checks, CORS
- [ ] Auth implications for B2/B3 tied to FR-10, FR-11 (Track E in #28)
- [ ] RLS policy outline for B3 (Alembic SQL migrations in #34)
- [ ] `.env.example` template (do not commit secrets)

---

## Default recommendation to document

**B0 or B1** until v3 schema frozen. Defer **B2/B3** until auth contract is stable (PR #27 invested in local JWT + `Users` table).

---

## Auth cross-reference (FR-10, FR-11)

| Topic | Impact on Supabase choice |
|-------|---------------------------|
| `UsersService.verify_credentials` | Missing today — required before any auth option |
| `PasswordManagerFactory` bootstrap | Required for B0/B1 local JWT path |
| JWT refresh/logout | B2/B3 may replace; B0/B1 need FR-11 decision |
| JWT `sub` claim | Map to `papita_transactions.users.id` |

Input: v0 audit §11 — `docs/design/PPT-031-v0-audit.md`

---

## References

- `modules/api/src/papita_txnsapi/config/settings.py`
- `modules/api/src/papita_txnsapi/core/security.py`
- Migrations: [#34](https://github.com/Elmorralito/save-ma-money/issues/34)
- Docker Postgres: `docker/database/docker-compose.yml`
