**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-045** · **Step:** Post-MVP ops packaging

## Summary

Standardize how `papita_txnsapi` is **launched under uvicorn** for B0 Compose. Uvicorn runs **inside the API Docker image** (not as a host Poetry process). The gap closed here is **canonical Make entrypoints**, Settings/`HOST`/`PORT` vs Dockerfile bind clarity, worker guidance (especially vs Redis in-memory fallbacks), and runbook clarity so paths do not drift.

## Current state (inspected)

| Surface       | Today                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ASGI app      | `papita_txnsapi.main:app` + lifespan (password manager + optional Redis)                                                                               |
| Dep           | `uvicorn[standard]` in `modules/api/pyproject.toml`                                                                                                    |
| Compose image | `docker/api/Dockerfile` → `CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]` (literal; Settings `HOST`/`PORT` unused) |
| Make          | `api-up` (Compose `api` + deps) / `stack-up` / `redis-up` / `redis-smoke`                                                                              |
| Poetry        | No host serve script — runtime is Docker                                                                                                               |
| Settings      | `HOST`, `PORT`, `PAPITA_ENV`, DB/Auth/Redis already on `Settings`                                                                                      |

## Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) — parent epic
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-043) — Redis lifespan + `/health/redis` / ready contract (coordinate; do not regress)
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) (PPT-044) — related ops hardening (CORS/TrustedHost); keep scopes distinct

## Blocks

- Cleaner local DX for Auth smoke / Redis smoke against a consistently started API container
- Safer multi-replica notes before anyone enables `--workers` without Redis rate limits

## Platform rule (B0 + B1)

Validate process packaging on **B0 Docker Postgres** (and Compose Redis when enabled). Supabase remains **Auth-only** for MVP; do not require pooler DB for this issue. Staging/prod notes may document managed Redis + uvicorn flags without deploying K8s.

## Decisions to lock in this issue

1. **Canonical entrypoint** — `make api-up` → Compose `api` service (uvicorn in-container). `make stack-up` for full explicit stack.
2. **No host uvicorn for B0** — do not promote `poetry run uvicorn` as a day-to-day path; container `CMD` is SSOT.
3. **Compose `HOST`/`PORT`** — **documented exception**: literal `0.0.0.0:8000` (HEALTHCHECK / `EXPOSE` / `${API_PORT}:8000` publish). Settings `HOST`/`PORT` are optional metadata.
4. **Reload policy** — never `--reload` in Compose `CMD`.
5. **Workers** — B0 default **single worker**. Document: in-memory rate limiter is process-local; multi-worker requires `REDIS_RATE_LIMIT_ENABLED=true` (+ Redis denylist). Defer gunicorn+uvicorn-workers unless justified.
6. **Lifecycle** — uvicorn must run the FastAPI lifespan (Redis init/teardown).
7. **Health contract unchanged** — `/api/v1/health`, `/ready`, `/live`, `/redis` remain smoke targets (`make redis-smoke`).

## Tasks / deliverables

### Ops / infra

- [x] Add Makefile target(s): `api-up` (Compose API container), document relationship to `stack-up` / `redis-up`
- [x] Document that runtime is Docker (no Poetry console serve script for B0)
- [x] Align Dockerfile/Compose CMD with `HOST`/`PORT` env (or document why flags stay literal `0.0.0.0:8000`)
- [x] Ensure Compose `api` service does not inject host `REDIS_URL=localhost` (already hardcoded `redis://redis:6379/0` — keep)

### Docs

- [x] Update `modules/api/README.md` run sections: Docker-canonical paths
- [x] Update `environments/README.md` with Compose Redis URL + uvicorn-in-container notes
- [x] Short ops note on workers vs Redis rate-limit / denylist fail-closed

### API package (minimal)

- [x] No `__main__.py` / host serve script — Make + Dockerfile `CMD` is enough

## API / infra integration

- [x] B0: `make api-up` → `/health/ready` true; optional `make redis-smoke`
- [x] B0: `make stack-up` → container healthcheck + ready
- [x] Env examples document `HOST`/`PORT` as metadata and `API_PORT` for publish
- [x] No secrets committed (`.env` stays gitignored)

## Requirements traceability

| ID      | Scope                                           |
| ------- | ----------------------------------------------- |
| NFR-04  | Operability — reproducible Compose start        |
| NFR-ops | Process packaging; readiness probes remain gate |
| PPT-043 | Lifespan Redis pool must start under uvicorn    |

## Out of scope

- Kubernetes / ECS / systemd unit files
- TLS termination / reverse proxy (Caddy, nginx, Traefik)
- gunicorn + uvicorn worker fleet (unless a short ADR justifies it)
- Changing REST routes or business logic in `papita_txnsmodel`
- Registrar, DuckDB, RLS (B3)
- Full PPT-044 security pack (CORS/TrustedHost/docs lockdown) — track on #89
- Host Poetry uvicorn as a supported B0 runtime

## Acceptance criteria

- [x] Documented canonical Compose command(s) (`make api-up` / `make stack-up`)
- [x] Dockerfile/Compose CMD aligned with Settings `HOST`/`PORT` **or** explicitly documented exception
- [x] Make convenience target(s) that start uvicorn **in Docker**
- [x] Worker guidance written (single-worker default; Redis required before multi-worker)
- [x] B0 smoke: API container up → ready → optional `make redis-smoke`
- [x] README (+ env README) updated; no secrets in git

## References

- `modules/api/src/papita_txnsapi/main.py` — `create_app`, lifespan, module `app`
- `docker/api/Dockerfile` — uvicorn `CMD` + live healthcheck
- `docker/docker-compose.yml` — `api` service env (Auth, DB, Redis)
- `Makefile` — `api-up`, `api-down`, `stack-up`, `redis-up`, `redis-smoke`
- `modules/api/README.md` — Compose run paths
- [#83](https://github.com/Elmorralito/save-ma-money/issues/83) PPT-043 Redis
- [#89](https://github.com/Elmorralito/save-ma-money/issues/89) PPT-044 hardening
- Epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42) PPT-032
