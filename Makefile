POETRY_ACTIVE ?= 0
VIRTUAL_ENV ?=
PYTHON_CMD := $(shell if [ "$(POETRY_ACTIVE)" = "1" ] || [ -n "$(VIRTUAL_ENV)" ]; then echo "python"; else echo "python -m poetry"; fi)
POETRY_CMD := $(shell if command -v poetry >/dev/null 2>&1; then echo poetry; else echo "python -m poetry"; fi)
PBCOPY_COMMAND := $(shell if test -e "$(shell which pbcopy)"; then echo "pbcopy"; else echo "xclip -selection clipboard"; fi)

prep:
	$(POETRY_CMD) env info || python -m pip install poetry

dev: prep
	$(PYTHON_CMD) lock --no-cache
	$(PYTHON_CMD) install

lite-dev: prep
	$(PYTHON_CMD) lock
	$(PYTHON_CMD) install

activate: prep
	echo "eval \"$(shell $(PYTHON_CMD) env activate)\"" | exec $(PBCOPY_COMMAND)

COMPOSE_LOCAL := env -u ALLOWED_ORIGINS docker compose --env-file environments/local/.env -f docker/docker-compose.yml

include bin/make/api.mk
include bin/make/web.mk
include bin/make/ingestor.mk
