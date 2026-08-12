# Papita email ingestion Prefect worker (PPT-082 / #176)
# Build context: repository root
#   docker compose --profile ingestor …  OR  docker build -f docker/ingestor/Dockerfile
#
# Installs model + ingestor-core[prefect] + email only (not API / web).

FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pip>=26.1.2" "setuptools>=78.1.1"

COPY modules/model/pyproject.toml modules/model/README.md modules/model/LICENSE /app/modules/model/
COPY modules/model/src /app/modules/model/src
COPY modules/model/alembic /app/modules/model/alembic
COPY modules/model/alembic.ini /app/modules/model/

COPY modules/ingestor-core/pyproject.toml modules/ingestor-core/README.md modules/ingestor-core/LICENSE /app/modules/ingestor-core/
COPY modules/ingestor-core/src /app/modules/ingestor-core/src

COPY modules/ingestors/email/pyproject.toml modules/ingestors/email/README.md modules/ingestors/email/LICENSE /app/modules/ingestors/email/
COPY modules/ingestors/email/src /app/modules/ingestors/email/src

RUN pip install --no-cache-dir \
        "/app/modules/model" \
        "/app/modules/ingestor-core[prefect]" \
        "/app/modules/ingestors/email" \
    && pip install --no-cache-dir --upgrade "setuptools>=78.1.1" \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1 \
    PREFECT_LOGGING_LEVEL=INFO \
    PREFECT_HOME=/tmp/prefect \
    PREFECT_RUNNER_SERVER_HOST=127.0.0.1 \
    PREFECT_RUNNER_SERVER_PORT=8080 \
    HOME=/tmp

EXPOSE 8080

USER appuser

# Runner /health for Compose HEALTHCHECK (flow.serve webserver=True).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"]

# Default: Prefect serve (hourly). Override command with --once for one-shot.
# Env vars come from Compose (environments/ is not copied into the image).
CMD ["python", "-m", "papita_ingestor_email.flows.email_flow"]
