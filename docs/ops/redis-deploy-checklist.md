# Redis B0 deploy checklist (PPT-043)

Local Redis is part of the Compose stack. Managed Redis is used for staging/prod.

## B0 — Docker Compose

```bash
cp environments/local/.env.example environments/local/.env
# Ensure REDIS_ENABLED=true and REDIS_URL=redis://localhost:6379/0 for host uvicorn

# Full stack (API Redis URL is hardcoded to redis://redis:6379/0)
make stack-up
make redis-smoke

# Or infra only + host API
make redis-up
# then: uvicorn with PAPITA_ENV=local (reads environments/local/.env)
```

| Piece                          | Path                                                               |
| ------------------------------ | ------------------------------------------------------------------ |
| Redis image + volume           | `docker/docker-compose.yml` / `docker/database/docker-compose.yml` |
| Server config (AOF, maxmemory) | `docker/redis/redis.conf`                                          |
| Smoke script                   | `bin/redis_smoke.sh`                                               |

## B1 — Managed Redis

1. Provision Upstash / ElastiCache / compatible Redis 7 with TLS.
2. Set in `environments/staging/.env` or `production/.env` (never commit):

```bash
REDIS_URL="rediss://default:<password>@<host>:6379"
REDIS_ENABLED="true"
REDIS_RATE_LIMIT_ENABLED="true"
REDIS_CACHE_TTL_ACCOUNTS_SECONDS="60"
REDIS_CACHE_TTL_CATEGORIES_SECONDS="300"
REDIS_CACHE_TTL_REPORTS_SECONDS="180"
REDIS_CACHE_TTL_TRANSACTIONS_SECONDS="15"
REDIS_MAX_CONNECTIONS="10"
# PAPITA_ENV=staging|production — all keys are papita:{env}:…
```

3. Restart API; confirm `GET /api/v1/health/redis` → `api-redis link healthy`.
4. Postgres remains source of truth; Redis is additive (cache, rate limits, JWT denylist).

## Hardening notes

| Concern                   | Policy                                         |
| ------------------------- | ---------------------------------------------- |
| Key prefix                | `papita:{PAPITA_ENV}:…` (isolate shared Redis) |
| Rate limit                | Atomic Lua ZSET (no multi-pipeline race)       |
| Cache / rate-limit errors | Fail open                                      |
| JWT denylist errors       | Fail closed (503) when `REDIS_ENABLED`         |
| Client                    | Sync `redis` for now; `redis.asyncio` later    |

## App wiring

| Capability                                | Flag / path                                   |
| ----------------------------------------- | --------------------------------------------- |
| Connection pool                           | `REDIS_ENABLED` + lifespan `init_redis`       |
| Distributed auth/API rate limits          | `REDIS_RATE_LIMIT_ENABLED` + Lua limiter      |
| Cache-aside (per-route TTL)               | automatic when Redis enabled                  |
| JWT denylist on logout / protected routes | `SessionStore` fail-closed when Redis enabled |
