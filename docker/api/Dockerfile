# Papita Transactions API — B0 local / B1 pooler runtime
# Build context: repository root (docker compose: context: .., dockerfile: docker/api/Dockerfile)

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pip>=25.0"

# Model package (includes Alembic migrations and config data)
COPY modules/model/pyproject.toml modules/model/README.md modules/model/LICENSE /app/modules/model/
COPY modules/model/src /app/modules/model/src
COPY modules/model/alembic /app/modules/model/alembic
COPY modules/model/alembic.ini /app/modules/model/

# API package
COPY modules/api/pyproject.toml modules/api/README.md modules/api/LICENSE /app/modules/api/
COPY modules/api/src /app/modules/api/src

RUN pip install --no-cache-dir /app/modules/model /app/modules/api

WORKDIR /app/modules/api/src

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live')" || exit 1

CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]
