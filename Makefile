POETRY_ACTIVE ?= 0
VIRTUAL_ENV ?=
VERSION ?= prerelease
MOD ?= ALL
PYTHON_CMD := $(shell if [ "$(POETRY_ACTIVE)" = "1" ] || [ -n "$(VIRTUAL_ENV)" ]; then echo "python"; else echo "python -m poetry"; fi)
POETRY_CMD := $(shell if [ "$(POETRY_ACTIVE)" = "1" ] || [ -n "$(VIRTUAL_ENV)" ]; then echo "python -m poetry"; else echo "python -m poetry"; fi) # Always use python -m poetry for safety
PBCOPY_COMMAND := $(shell if test -e "$(shell which pbcopy)"; then echo "pbcopy"; else echo "xclip -selection clipboard"; fi)

prep:
	$(POETRY_CMD) env info || python -m pip install poetry

dev: prep
	$(PYTHON_CMD) lock --no-cache
	$(PYTHON_CMD) install

dev-version:
	./bin/version.sh --version $(VERSION) --mod $(MOD)

# Build sdist + wheel for modules/model only → dist/ (PPT-024 / PyPI).
package-model:
	/bin/bash ./bin/package.sh --mod model

lite-dev: prep
	$(PYTHON_CMD) lock
	$(PYTHON_CMD) install

activate: prep
	echo "eval \"$(shell $(PYTHON_CMD) env activate)\"" | exec $(PBCOPY_COMMAND)

# Legacy optional pooler smoke (not Auth-first / not PPT-040 AC). Prefer: make auth-smoke
b1-smoke:
	/bin/bash ./bin/b1_smoke.sh

# Manual Supabase Auth JWT smoke against a running API (Auth-only DoD; not a DB gate).
auth-smoke:
	/bin/bash ./bin/auth_smoke.sh

# B0 Postgres + Redis only (no API container). Useful when poking Redis from the host.
redis-up:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d redis

redis-down:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml stop redis

COMPOSE_LOCAL := docker compose --env-file environments/local/.env -f docker/docker-compose.yml

# Canonical API runtime (PPT-045): uvicorn runs inside the Compose image — not on the host.
# Brings up api + depends_on (Postgres, Redis, migrate). Bind: 0.0.0.0:8000 in-container;
# host publish via API_PORT (environments/local/.env). No --reload / --workers in the container.
api-up:
	$(COMPOSE_LOCAL) up --build -d api

api-down:
	$(COMPOSE_LOCAL) stop api

# Full B0 stack (explicit up of all services in docker/docker-compose.yml).
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
	/bin/bash ./bin/redis_smoke.sh

# Web SPA (PPT-047): Vite + React under modules/web (pnpm workspace).
# Requires Node 22+ and pnpm 9 (see modules/web/README.md). API optional for lint/test/build.
web-dev:
	pnpm web:dev

web-lint:
	pnpm web:lint

web-test:
	pnpm web:test

web-build:
	pnpm web:build

# OpenAPI typegen strategy B (PPT-065 / #130): committed artifact + generated TS types.
# Offline dump — no Compose/DB. After API schema changes: sync-openapi && generate-types.
sync-openapi:
	/bin/bash ./bin/export_openapi.sh

check-openapi:
	/bin/bash ./bin/export_openapi.sh --check

# Optional live fetch (docs must be enabled on the running API). Prefer sync-openapi.
sync-openapi-live:
	/bin/bash ./bin/export_openapi.sh --from-url http://localhost:8000/api/openapi.json

generate-types:
	pnpm web:generate-types

check-types:
	pnpm web:check-types

# Full local contract refresh used after API OpenAPI-affecting changes.
web-openapi: sync-openapi generate-types

# E2E fixtures (PPT-061 / #126): HTTP seed against a running Compose API.
# Requires: make api-all (AUTH_PROVIDER=local recommended for B0 CI).
# Idempotent upsert; RESET=1 soft-deletes baseline txns + E2E accounts (categories reused).
# Artifact: modules/web/e2e/.auth/seed.json (gitignored) for Playwright #121.
RESET ?= 0
web-e2e-seed:
	RESET=$(RESET) /bin/bash ./bin/web_e2e_seed.sh

# Vitest coverage gate (PPT-056 / #121) — thresholds in modules/web/vite.config.ts.
web-test-coverage:
	pnpm web:test:coverage

# Playwright critical path + axe (PPT-056). Requires: make api-all (seed via globalSetup).
web-e2e:
	pnpm web:test:e2e

# Lighthouse CI lab budgets against vite preview (build first).
web-lhci: web-build
	pnpm web:lhci

# Production dependency audit for @papita/web (Dependabot npm-web covers PRs).
web-audit:
	pnpm web:audit
