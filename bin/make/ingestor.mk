# Ingestor domain slice targets (PPT-098 — merged into backend/).

ingestor-install: prep
	$(POETRY_CMD) install --no-interaction --with development

ingestor-flow-install: ingestor-install

ingestor-test:
	$(POETRY_CMD) run pytest \
		backend/tests/ingestor_core \
		backend/tests/ingestor_email \
		-q --no-cov

ingestor-lint:
	$(POETRY_CMD) run black --check \
		backend/src/papita_ingestor_core \
		backend/src/papita_ingestor_email \
		backend/tests/ingestor_core \
		backend/tests/ingestor_email
	$(POETRY_CMD) run isort --check-only \
		backend/src/papita_ingestor_core \
		backend/src/papita_ingestor_email \
		backend/tests/ingestor_core \
		backend/tests/ingestor_email
	$(POETRY_CMD) run flake8 \
		backend/src/papita_ingestor_core \
		backend/src/papita_ingestor_email
	$(POETRY_CMD) run pylint \
		backend/src/papita_ingestor_core \
		backend/src/papita_ingestor_email

# One-shot email ingestion (requires env: PAPITA_INGESTOR_OWNER_ID, GMAIL_*, DATABASE_URL).
ingestor-flow:
	$(POETRY_CMD) run python -m backend.domains.ingestion.cli --once

ingestor-flow-serve:
	$(POETRY_CMD) run python -m backend.domains.ingestion.cli

# Optional Compose worker (does not start with make api-up).
ingestor-up:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make ingestor-up"; \
		exit 1; \
	}
	$(COMPOSE_LOCAL) --profile ingestor up --build -d ingestor

ingestor-down:
	$(COMPOSE_LOCAL) --profile ingestor stop ingestor
