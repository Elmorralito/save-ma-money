# API / B0 Compose runtime targets (PPT-032 / PPT-045). Path-filter consumers
# (e.g. publish-api-image.yml) watch bin/make/api.mk — not the whole root Makefile.

# Legacy optional pooler smoke (not Auth-first / not PPT-040 AC). Prefer: make auth-smoke
b1-smoke:
	./bin/bash/b1_smoke.sh

# Manual Supabase Auth JWT smoke against a running API (Auth-only DoD; not a DB gate).
auth-smoke:
	./bin/bash/auth_smoke.sh

# B0 Postgres + Redis only (no API container). Useful when poking Redis from the host.
redis-up:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d redis

redis-down:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml stop redis

# Build API image only (local tag; no registry). See docker/README.md (PPT-067).
api-image-build:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make api-image-build"; \
		exit 1; \
	}
	docker build -f docker/api/Dockerfile -t papita-api:local .

# Canonical API runtime (PPT-045): uvicorn runs inside the Compose image — not on the host.
# Brings up api + depends_on (Postgres, Redis, migrate). Bind: 0.0.0.0:8000 in-container;
# host publish via API_PORT (environments/local/.env). No --reload / --workers in the container.
# Registry publish (GHCR) is PPT-067 — not required for B0; see docker/README.md.
api-up:
	$(COMPOSE_LOCAL) up --build -d api

api-down:
	$(COMPOSE_LOCAL) stop api

# Full B0 stack (explicit up of all services in docker/docker-compose.yml),
# including nginx SPA when `web` is defined (PPT-057 / #122).
stack-up:
	$(COMPOSE_LOCAL) up --build -d

stack-down:
	$(COMPOSE_LOCAL) down

# Bring up the entire API stack (Postgres + Redis + migrate + api), wait until healthy.
# Prefer this for local SPA/BFF work when you want every API dependency running.
api-all:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make api-all"; \
		exit 1; \
	}
	$(COMPOSE_LOCAL) up --build -d
	@API_PORT=$$(grep -E '^API_PORT=' environments/local/.env 2>/dev/null | cut -d= -f2); \
	API_PORT=$${API_PORT:-8000}; \
	echo "Waiting for API on :$${API_PORT}…"; \
	i=0; \
	while [ $$i -lt 60 ]; do \
		if curl -sf "http://localhost:$${API_PORT}/api/v1/health/live" >/dev/null 2>&1; then \
			echo "API ready: http://localhost:$${API_PORT}/api/docs"; \
			echo "Health:    http://localhost:$${API_PORT}/api/v1/health"; \
			exit 0; \
		fi; \
		i=$$((i + 1)); \
		sleep 2; \
	done; \
	echo "API did not become healthy in time. Try: $(COMPOSE_LOCAL) logs api"; \
	exit 1

# Tear down the full Compose project started by api-all / stack-up.
api-all-down: stack-down

# Redis readiness smoke against a running API container (make api-up / stack-up).
redis-smoke:
	./bin/bash/redis_smoke.sh
