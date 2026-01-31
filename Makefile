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

cov-badge:
	/bin/bash ./deploy/test.sh && genbadge coverage -i ./docs/coverage.xml -o ./docs/coverage-badge.svg

flake8-badge:
	flake8 ./modules/ --exit-zero --format=html --htmldir ./docs/.flake8 --statistics --tee --output-file ./docs/.flake8/report.txt && \
	genbadge flake8 -i ./docs/.flake8/report.txt -o ./docs/flake8-badge.svg

badges: cov-badge flake8-badge
