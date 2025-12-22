MOD?=ALL
VERSION?=prerelease
PBCOPY_COMMAND := $(shell if test -e "$(shell which pbcopy)"; then echo "pbcopy"; else echo "xclip -selection clipboard"; fi)

prep:
	python -m poetry env info || python -m pip install poetry

dev: prep
	python -m poetry lock --no-cache
	python -m poetry install

dev-version:
	./deploy/version.sh --version $(VERSION) --mod $(MOD)

lite-dev: prep
	python -m poetry lock
	python -m poetry install

activate: prep
	echo "eval \"$(shell python -m poetry env activate)\"" | exec $(PBCOPY_COMMAND)

cov-badge:
	/bin/bash ./deploy/test.sh && genbadge coverage -i ./docs/coverage.xml -o ./docs/coverage-badge.svg

flake8-badge:
	flake8 ./modules/ --exit-zero --format=html --htmldir ./docs/.flake8 --statistics --tee --output-file ./docs/.flake8/report.txt && \
	genbadge flake8 -i ./docs/.flake8/report.txt -o ./docs/flake8-badge.svg

badges: cov-badge flake8-badge
