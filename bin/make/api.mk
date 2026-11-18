# API / B0 Compose runtime targets (PPT-032 / PPT-045 / PPT-100).

# Manual Supabase Auth JWT smoke against a running API.
auth-smoke:
	./bin/bash/auth_smoke.sh

# B0 Postgres + Redis only (no API container).
redis-up:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d redis

redis-down:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml stop redis

# Build API image only (local tag; no registry).
api-image-build:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make api-image-build"; \
		exit 1; \
	}
	docker build -f docker/api/Dockerfile -t papita-api:local .

api-up:
	$(COMPOSE_LOCAL) up --build -d api

api-down:
	$(COMPOSE_LOCAL) stop api

stack-up:
	$(COMPOSE_LOCAL) up --build -d

stack-down:
	$(COMPOSE_LOCAL) down

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

api-all-down: stack-down
