MOD?=ALL
VERSION?=prerelease
PBCOPY_COMMAND := $(shell if test -e "$(shell which pbcopy)"; then echo "pbcopy"; else echo "xclip -selection clipboard"; fi)

prep:
	python -m poetry env info || python -m pip install poetry

dev: prep
	python -m poetry lock --no-cache
	python -m poetry install

lite-dev: prep
	python -m poetry lock
	python -m poetry install

activate: prep
	echo "eval \"$(shell python -m poetry env activate)\"" | exec $(PBCOPY_COMMAND)

cov-badge:
	/bin/bash ./deploy/test.sh && genbadge coverage -i ./docs/coverage.xml -o ./docs/coverage-badge.svg

dev-version:
	./deploy/version.sh --version $(VERSION) --mod $(MOD)
