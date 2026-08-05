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

# Prefer environments/local/.env over a polluted shell (Compose shell env wins over
# --env-file for ${VAR} interpolation). Stale ALLOWED_ORIGINS without :5173 breaks
# Vite BFF OAuth cookies/redirects.
COMPOSE_LOCAL := env -u ALLOWED_ORIGINS docker compose --env-file environments/local/.env -f docker/docker-compose.yml

# Build API image only (local tag; no registry). See docker/README.md (PPT-067).
api-image-build:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make api-image-build"; \
		exit 1; \
	}
	docker build -f docker/api/Dockerfile -t papita-api:local .

# Build web nginx image only (local tag; no registry). Multi-stage pnpm → nginx.
web-image-build:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make web-image-build"; \
		exit 1; \
	}
	docker build -f docker/web/Dockerfile \
		--build-arg VITE_APP_TITLE=Papita \
		--build-arg VITE_PAPITA_BREAKING_CHANGES_ID=ppt-044 \
		--build-arg VITE_API_BASE_URL= \
		-t papita-web:local .


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

# nginx SPA packaging (PPT-057 / #122): multi-stage pnpm build → nginx:alpine.
# Brings up `web` + depends_on (api, redis, postgres, migrate). Same-origin /api
# proxy preserves BFF HttpOnly cookies (papita_sid Path=/api). Prefer this over
# host Vite when validating Compose packaging; day-to-day DX remains `make web-dev`.
web-up:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make web-up"; \
		exit 1; \
	}
	$(COMPOSE_LOCAL) up --build -d web
	@WEB_PORT=$$(grep -E '^WEB_PORT=' environments/local/.env 2>/dev/null | cut -d= -f2); \
	WEB_PORT=$${WEB_PORT:-3000}; \
	echo "Waiting for nginx SPA on :$${WEB_PORT}…"; \
	i=0; \
	while [ $$i -lt 90 ]; do \
		if curl -sf "http://localhost:$${WEB_PORT}/" >/dev/null 2>&1 \
			&& curl -sf "http://localhost:$${WEB_PORT}/api/v1/health/live" >/dev/null 2>&1; then \
			HDRS=$$(curl -sI "http://localhost:$${WEB_PORT}/"); \
			echo "$$HDRS" | grep -qi '^content-security-policy:' \
				&& echo "$$HDRS" | grep -F "script-src 'self'" >/dev/null \
				&& echo "$$HDRS" | grep -F "frame-ancestors 'none'" >/dev/null \
				&& echo "$$HDRS" | grep -qi '^x-content-type-options: *nosniff' \
				&& echo "$$HDRS" | grep -qi '^referrer-policy: *no-referrer' \
				&& echo "$$HDRS" | grep -qi '^x-frame-options: *DENY' \
				|| { echo "SPA security headers missing on / (PPT-063). Check docker/web/nginx.conf"; exit 1; }; \
			echo "Web ready:     http://localhost:$${WEB_PORT}/"; \
			echo "API via nginx: http://localhost:$${WEB_PORT}/api/v1/health"; \
			echo "CSP smoke:     OK (PPT-063)"; \
			exit 0; \
		fi; \
		i=$$((i + 1)); \
		sleep 2; \
	done; \
	echo "Web did not become healthy in time. Try: $(COMPOSE_LOCAL) logs web api"; \
	exit 1

web-down:
	$(COMPOSE_LOCAL) stop web

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
