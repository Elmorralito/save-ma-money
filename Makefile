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

# B0 Postgres + Redis (no API). Host uvicorn uses REDIS_URL=redis://localhost:6379/0
redis-up:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml up -d redis

redis-down:
	docker compose --env-file environments/local/.env -f docker/database/docker-compose.yml stop redis

# Full B0 stack (Postgres + Redis + migrate + API). API Redis is on by default.
stack-up:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml up --build -d

stack-down:
	docker compose --env-file environments/local/.env -f docker/docker-compose.yml down

# Redis readiness smoke against a running API (Compose or host).
redis-smoke:
	/bin/bash ./bin/redis_smoke.sh
