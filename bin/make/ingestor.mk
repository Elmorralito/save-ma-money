# Ingestor domain slice targets (PPT-098 / PPT-100 — merged into backend/).

ingestor-install: prep
	$(POETRY_CMD) install --no-interaction --with development

ingestor-flow-install: ingestor-install

ingestor-test:
	$(POETRY_CMD) run pytest \
		backend/tests/ingestor_core \
		backend/tests/ingestor_email \
		-q --no-cov

ingestor-lint:
	$(POETRY_CMD) run ruff check \
		backend/src/papita_ingestor_core \
		backend/src/papita_ingestor_email \
		backend/tests/ingestor_core \
		backend/tests/ingestor_email

ingestor-flow:
	$(POETRY_CMD) run python -m backend.domains.ingestion.cli --once

ingestor-flow-serve:
	$(POETRY_CMD) run python -m backend.domains.ingestion.cli

ingestor-up:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is not running. Start Docker Desktop, then retry: make ingestor-up"; \
		exit 1; \
	}
	$(COMPOSE_LOCAL) --profile ingestor up --build -d ingestor

ingestor-down:
	$(COMPOSE_LOCAL) --profile ingestor stop ingestor
