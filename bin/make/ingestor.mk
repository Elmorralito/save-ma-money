# Ingestor packages (PPT-077 / #171). Path-filtered by ingestor-ci.yml → bin/make/ingestor.mk.
# Gate is ingestor-ci (not quality-control); QC paths-ignore covers modules/ingestor*.

ingestor-install: prep
	$(POETRY_CMD) install --no-interaction --with development

ingestor-test:
	# --no-cov: root pytest.ini addopts covers model/api only (PPT-084 owns ingestor cov).
	$(POETRY_CMD) run pytest \
		modules/ingestor-core/tests \
		modules/ingestors/email/tests \
		-q --no-cov

ingestor-lint:
	$(POETRY_CMD) run black --check \
		modules/ingestor-core/src \
		modules/ingestors/email/src \
		modules/ingestor-core/tests \
		modules/ingestors/email/tests
	$(POETRY_CMD) run isort --check-only \
		modules/ingestor-core/src \
		modules/ingestors/email/src \
		modules/ingestor-core/tests \
		modules/ingestors/email/tests
	$(POETRY_CMD) run flake8 \
		modules/ingestor-core/src \
		modules/ingestors/email/src
	$(POETRY_CMD) run pylint \
		modules/ingestor-core/src \
		modules/ingestors/email/src
