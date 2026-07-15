**Parent program:** #28 (PPT-031) · **Parent epic:** #42 (PPT-032) · **PPT-039** · **Step:** 6 (Auth = Supabase)

## Summary

Replace local HS256 issuance (`AuthSecurityManager` + `JWT_SECRET_KEY`) with **Supabase Auth**. FastAPI validates Supabase JWTs and maps `sub` → `papita_transactions.users` / tenant `owner`. Database hosting remains **Docker Postgres (B0) or any Postgres URL** — **not** in scope for this issue.

**Supersedes prior #49 focus** (Supabase transaction pooler / B1 DB wiring). Landed pooler docs/engine/smoke are dispositioned below — do not redo as AC here.

Canonical write-up in-repo: [`docs/issues/PPT-039-supabase-auth-reissue.md`](https://github.com/Elmorralito/save-ma-money/blob/main/docs/issues/PPT-039-supabase-auth-reissue.md)

## Depends on

- #44 (PPT-035) — auth + tenant module (exists; this issue rewires it)
- Soft: G5 auth-contract update noting Supabase Auth as MVP choice
- Soft: #89 for prod CORS/docs posture when Auth is public

## Blocks

- #50 (PPT-040) — CI secrets become Supabase Auth (`SUPABASE_URL` / JWKS + test project), not required pooler `DATABASE_URL`
- Cleaner epic #42 AC (Auth, not pooler DB)

## Platform rule (updated)

| Layer          | Local / CI                             | Staging / prod                                                           |
| -------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| **Database**   | Docker Postgres (or any PG URL)        | Same app; **any** hosted Postgres (Supabase PG _optional_, not required) |
| **Auth**       | Supabase Auth (project or local stack) | Supabase Auth                                                            |
| **Migrations** | `./deploy/alembic.sh --env local`      | Direct PG URL — independent of Auth                                      |

## Disposition of prior B1 DB work (landed)

| Item                                                                                 | Disposition                                                                             |
| ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `environments/*` pooler templates, checklist, `pool_pre_ping` / `DATABASE_POOL_SIZE` | **Keep** as optional ops; not MVP AC                                                    |
| `test_supabase_b1_smoke.py` / `make b1-smoke`                                        | **Park or narrow** to Auth smoke against Supabase JWT; DB pooler smoke → optional / #50 |
| Epic wording “validate on Supabase pooler”                                           | **Remove** via #42 edit                                                                 |

## Tasks / deliverables

### Settings & env (`PAPITA_ENV`)

- [ ] Document `SUPABASE_URL`, JWT verification mode (JWKS preferred), deprecate app-issued `JWT_SECRET_KEY` for access tokens (or transitional feature flag)
- [ ] Update `environments/{local,staging,production}/.env.example` — Auth vars primary; pooler URLs secondary/commented

### Runtime

- [ ] `AuthSecurityManager.decode_token` (or successor) validates Supabase JWT (`aud` / `iss` / `sub`)
- [ ] Register/login: prefer **client → Supabase Auth**, API verifies Bearer only; thin pass-through optional
- [ ] `get_current_owner`: `sub` → ensure/link `UsersDTO` (provision-on-first-seen; prefer UUID alignment)
- [ ] Keep `/health/live` DB-free; ready stays DB probe (unchanged)

### Tests & docs

- [ ] Replace local JWT unit tests with JWKS/mock token fixtures
- [ ] Auth smoke: obtain Supabase token → `/auth/me` + one tenant list
- [ ] API README + auth contract Part VI + Strata; brief G7 supersede pointer

## Out of scope

- Requiring Supabase **Postgres** pooler for MVP
- RLS (B3), Redis, full PPT-044 pack
- OAuth provider matrix beyond email/password (follow-on)

## Acceptance criteria

- [ ] Title/semantic `feat/PPT-039`; epic #42 no longer requires Supabase-hosted DB
- [ ] Protected routes accept Supabase access JWT; local password JWT issuance removed or off by default
- [ ] Tenant isolation still `owner_id` via `sub` mapping
- [ ] Env templates document Auth secrets (values never in git)
- [ ] Handoff to #50: `SUPABASE_URL` (+ JWKS); smoke entrypoint named
- [ ] Prior pooler ACs explicitly waived or moved to parked ops

## References

- PPT-031-C §1.4 B2 + [G7 supersede](https://github.com/Elmorralito/save-ma-money/blob/main/docs/issues/PPT-031-C-supabase-decision-brief.md)
- `modules/api/.../security.py`, `routers/v1/auth.py`, `dependencies/auth.py`
- Epic #42 · CI #50 · brief G7 supersede on #28

## Handoff to PPT-040 (#50)

| Name                    | Role                                               |
| ----------------------- | -------------------------------------------------- |
| `SUPABASE_URL`          | Project URL for JWKS / Auth API                    |
| (optional) anon key     | Client-side Auth only                              |
| (optional) service role | Server-only provisioning — never expose to clients |
| `DATABASE_URL`          | Any Postgres — **not** tied to Supabase Auth       |

**Smoke entrypoint (target):** Auth JWT → `GET /api/v1/auth/me` (+ one tenant list).
