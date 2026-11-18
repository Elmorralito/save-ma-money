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

COPY backend/pyproject.toml backend/README.md backend/LICENSE /app/backend/
COPY backend/src /app/backend/src
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/

RUN pip install --no-cache-dir \
        "/app/backend" \
    && pip install --no-cache-dir --upgrade "setuptools>=78.1.1" \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp

USER appuser

CMD ["python", "-m", "backend.domains.ingestion.cli", "--once"]
