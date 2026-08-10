# Papita Transactions API - B0 local / B1 pooler runtime
# Build context: repository root (docker compose: context: .., dockerfile: docker/api/Dockerfile)
# Registry publish: GHCR via .github/workflows/publish-api-image.yml (PPT-067 / #132)
# Naming SSOT: docker/README.md
#
# Base digest pinned for supply-chain stability; Dependabot (docker /docker/api) refreshes it.

FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pip>=26.1.2" "setuptools>=78.1.1"

# Model package (includes Alembic migrations and config data)
COPY modules/model/pyproject.toml modules/model/README.md modules/model/LICENSE /app/modules/model/
COPY modules/model/src /app/modules/model/src
COPY modules/model/alembic /app/modules/model/alembic
COPY modules/model/alembic.ini /app/modules/model/

# API package
COPY modules/api/pyproject.toml modules/api/README.md modules/api/LICENSE /app/modules/api/
COPY modules/api/src /app/modules/api/src

# Upgrade transitive / base tooling after package install so Trivy CRITICAL/HIGH stays green
# (msgpack via redis stack; setuptools from python:slim base).
RUN pip install --no-cache-dir /app/modules/model /app/modules/api \
    && pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1" \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app

WORKDIR /app/modules/api/src

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live')"]

USER appuser

# Bind flags stay literal 0.0.0.0:8000 (HEALTHCHECK / EXPOSE / Compose publish assume :8000).
# Settings HOST/PORT are unused for bind; host-side API_PORT only remaps publish (${API_PORT}:8000).
# Never add --reload or --workers to this CMD (PPT-045 — single-worker Compose runtime).
CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]
