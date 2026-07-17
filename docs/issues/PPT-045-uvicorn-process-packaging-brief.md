**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-045** · **Step:** Post-MVP ops packaging

## Summary

Standardize how `papita_txnsapi` is **launched under uvicorn** for B0 Compose and host/dev. This is **not** “add uvicorn” — the dependency, Dockerfile `CMD`, and README one-liners already exist. The gap is **canonical entrypoints**, Settings/`HOST`/`PORT` alignment, Make/Poetry convenience targets, worker guidance (especially vs Redis in-memory fallbacks), and runbook clarity so local and Compose paths do not drift.

## Current state (inspected)

| Surface       | Today                                                                                                                                                     |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASGI app      | `papita_txnsapi.main:app` + lifespan (password manager + optional Redis)                                                                                  |
| Dep           | `uvicorn[standard]` in `modules/api/pyproject.toml`                                                                                                       |
| Compose image | `docker/api/Dockerfile` → `CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]` (hardcoded; ignores Settings `HOST`/`PORT`) |
| Host docs     | Ad-hoc `uvicorn … --reload` in `modules/api/README.md` / root README                                                                                      |
| Make          | `stack-up` / `redis-up` / `redis-smoke` exist; **no** `api-up` / host uvicorn target                                                                      |
| Poetry        | No `[project.scripts]` / console entry for API serve                                                                                                      |
| Settings      | `HOST`, `PORT`, `PAPITA_ENV`, DB/Auth/Redis already on `Settings`                                                                                         |

## Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) — parent epic
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-043) — Redis lifespan + `/health/redis` / ready contract (coordinate; do not regress)
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) (PPT-044) — related ops hardening (CORS/TrustedHost); keep scopes distinct

## Blocks

- Cleaner local DX for Auth smoke / Redis smoke against a consistently started API
- Safer multi-replica notes before anyone enables `--workers` without Redis rate limits

## Platform rule (B0 + B1)

Validate process packaging on **B0 Docker Postgres** (and Compose Redis when enabled). Supabase remains **Auth-only** for MVP; do not require pooler DB for this issue. Staging/prod notes may document managed Redis + uvicorn flags without deploying K8s.

## Decisions to lock in this issue

1. **Canonical host entrypoint** — prefer one of:
   - `make api-up` (PAPITA_ENV=local, reads `environments/local/.env`, `--reload` for dev), and/or
   - Poetry script e.g. `papita-api` / `poetry run papita-api`
2. **Canonical Compose path** — keep Dockerfile CMD; optionally shell-form or entrypoint that passes `$HOST`/`$PORT` from env to match Settings.
3. **Reload policy** — `--reload` **host/dev only**; never in Compose prod-like `CMD`.
4. **Workers** — B0 default **single worker**. Document: in-memory rate limiter is process-local; multi-worker requires `REDIS_RATE_LIMIT_ENABLED=true` (+ Redis denylist). Defer gunicorn+uvicorn-workers unless justified.
5. **Lifecycle** — uvicorn must run the FastAPI lifespan (Redis init/teardown); document graceful shutdown expectations.
6. **Health contract unchanged** — `/api/v1/health`, `/ready`, `/live`, `/redis` remain smoke targets (`make redis-smoke` when Redis on).

## Tasks / deliverables

### Ops / infra

- [ ] Add Makefile target(s): e.g. `api-up` (host uvicorn + reload), document relationship to `stack-up` / `redis-up`
- [ ] Optional Poetry console script or documented `poetry run uvicorn` wrapper with `cd`/PYTHONPATH clarity from repo root
- [ ] Align Dockerfile/Compose CMD with `HOST`/`PORT` env (or document why flags stay literal `0.0.0.0:8000`)
- [ ] Ensure Compose `api` service does not inject host `REDIS_URL=localhost` (already hardcoded `redis://redis:6379/0` — keep)

### Docs

- [ ] Update `modules/api/README.md` run sections: one host path, one Compose path; remove stale “when routers land”
- [ ] Update `environments/README.md` with host vs Compose Redis URL split + uvicorn notes
- [ ] Short ops note (README or `docs/ops/`) on workers vs Redis rate-limit / denylist fail-closed

### API package (minimal)

- [ ] Only if needed: tiny `__main__.py` or script module that reads Settings and execs uvicorn programmatically (optional; Make + uvicorn CLI is enough)

## API / infra integration

- [ ] B0: `make redis-up` + host `api-up` → `/health/ready` true; optional `make redis-smoke`
- [ ] B0: `make stack-up` → container healthcheck + ready
- [ ] Env examples already document `HOST`/`PORT` or explicitly defer to uvicorn flags
- [ ] No secrets committed (`.env` stays gitignored)

## Requirements traceability

| ID      | Scope                                           |
| ------- | ----------------------------------------------- |
| NFR-04  | Operability — reproducible local/Compose start  |
| NFR-ops | Process packaging; readiness probes remain gate |
| PPT-043 | Lifespan Redis pool must start under uvicorn    |

## Out of scope

- Kubernetes / ECS / systemd unit files
- TLS termination / reverse proxy (Caddy, nginx, Traefik)
- gunicorn + uvicorn worker fleet (unless a short ADR justifies it)
- Changing REST routes or business logic in `papita_txnsmodel`
- Registrar, DuckDB, RLS (B3)
- Full PPT-044 security pack (CORS/TrustedHost/docs lockdown) — track on #89

## Acceptance criteria

- [ ] Documented **one** canonical host command and **one** Compose path
- [ ] Dockerfile/Compose CMD aligned with Settings `HOST`/`PORT` **or** explicitly documented exception
- [ ] Make and/or Poetry convenience target(s) for local run
- [ ] Worker guidance written (single-worker default; Redis required before multi-worker)
- [ ] B0 smoke: API up → ready → optional `make redis-smoke`
- [ ] README (+ env README) updated; no secrets in git

## References

- `modules/api/src/papita_txnsapi/main.py` — `create_app`, lifespan, module `app`
- `docker/api/Dockerfile` — current uvicorn `CMD` + live healthcheck
- `docker/docker-compose.yml` — `api` service env (Auth, DB, Redis)
- `Makefile` — `stack-up`, `redis-up`, `redis-smoke`
- `modules/api/README.md` — host uvicorn snippets
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) PPT-043 Redis
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) PPT-044 hardening
- Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) PPT-032
