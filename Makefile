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

# Canonical API runtime (PPT-045): uvicorn runs inside the Compose image — not on the host.
# Brings up api + depends_on (Postgres, Redis, migrate). Bind: 0.0.0.0:8000 in-container;
# host publish via API_PORT (environments/local/.env). No --reload / --workers in the container.
api-up:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml up --build -d api

api-down:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml stop api

# Full B0 stack (explicit up of all services in docker/docker-compose.yml).
stack-up:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml up --build -d

stack-down:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml down

# Redis readiness smoke against a running API container (make api-up / stack-up).
redis-smoke:
	/bin/bash ./bin/redis_smoke.sh
