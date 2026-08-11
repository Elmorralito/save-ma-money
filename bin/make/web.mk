# Web SPA targets (PPT-046+). Path-filtered by web-ci.yml → bin/make/web.mk
# (not the root Makefile) so api/ingestor Make edits do not retrigger Web CI.

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
	./bin/bash/export_openapi.sh

check-openapi:
	./bin/bash/export_openapi.sh --check

# Optional live fetch (docs must be enabled on the running API). Prefer sync-openapi.
sync-openapi-live:
	./bin/bash/export_openapi.sh --from-url http://localhost:8000/api/openapi.json

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
	RESET=$(RESET) ./bin/bash/web_e2e_seed.sh

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
