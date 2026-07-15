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
	./deploy/version.sh --version $(VERSION) --mod $(MOD)

lite-dev: prep
	$(PYTHON_CMD) lock
	$(PYTHON_CMD) install

activate: prep
	echo "eval \"$(shell $(PYTHON_CMD) env activate)\"" | exec $(PBCOPY_COMMAND)

# Optional B1 pooler smoke (fails if gate not met). Plain pytest skips instead.
b1-smoke:
	/bin/bash ./deploy/b1_smoke.sh

# Manual Supabase Auth JWT smoke against a running API (not a CI B0 gate).
auth-smoke:
	/bin/bash ./deploy/auth_smoke.sh
