# Ingestor packages (PPT-077 / #171). Path-filtered by ingestor-ci.yml → bin/make/ingestor.mk.
# Gate is ingestor-ci (not quality-control); QC paths-ignore covers modules/ingestor*.
# Prefect flow packaging: PPT-082 / #176 (optional group ingestor-prefect).

ingestor-install: prep
	$(POETRY_CMD) install --no-interaction --with development

# Installs Prefect for email flow / Compose worker (root package-mode=false → no -E).
ingestor-flow-install: prep
	$(POETRY_CMD) install --no-interaction --with development,ingestor-prefect

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

# One-shot email ingestion (requires env: PAPITA_INGESTOR_OWNER_ID, GMAIL_*, DATABASE_URL).
# Loads environments/$(PAPITA_ENV)/.env inside the module (unless --skip-env-file).
# Install Prefect once via `make ingestor-flow-install` (not re-run every invocation).
ingestor-flow:
	$(POETRY_CMD) run python -m papita_ingestor_email.flows.email_flow --once

# Prefect serve (hourly by default). Prefer Compose profile `ingestor` for B0 worker.
ingestor-flow-serve:
	$(POETRY_CMD) run python -m papita_ingestor_email.flows.email_flow

# Optional Compose worker (does not start with make api-up).
ingestor-up:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make ingestor-up"; \
		exit 1; \
	}
	$(COMPOSE_LOCAL) --profile ingestor up --build -d ingestor

ingestor-down:
	$(COMPOSE_LOCAL) --profile ingestor stop ingestor
