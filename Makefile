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
	./bin/bash/version.sh --version $(VERSION) --mod $(MOD)

# Build sdist + wheel for modules/model only → dist/ (PPT-024 / PyPI).
package-model:
	./bin/bash/package.sh --mod model

lite-dev: prep
	$(PYTHON_CMD) lock
	$(PYTHON_CMD) install

activate: prep
	echo "eval \"$(shell $(PYTHON_CMD) env activate)\"" | exec $(PBCOPY_COMMAND)

# Prefer environments/local/.env over a polluted shell (Compose shell env wins over
# --env-file for ${VAR} interpolation). Stale ALLOWED_ORIGINS without :5173 breaks
# Vite BFF OAuth cookies/redirects. Shared by bin/make/api.mk and bin/make/web.mk.
COMPOSE_LOCAL := env -u ALLOWED_ORIGINS docker compose --env-file environments/local/.env -f docker/docker-compose.yml

# Domain Make fragments under bin/ (PPT-077 / #171): CI path-filters watch the
# specific *.mk file — not this root Makefile — so unrelated Make edits stay quiet.
include bin/make/api.mk
include bin/make/web.mk
include bin/make/ingestor.mk
