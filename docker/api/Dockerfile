# Papita Transactions API - B0 local / B1 pooler runtime
# Build context: repository root (docker compose: context: .., dockerfile: docker/api/Dockerfile)
# Registry publish: GHCR via .github/workflows/publish-api-image.yml (PPT-067 / #132)
# Naming SSOT: docker/README.md
#
# Base digest pinned for supply-chain stability; Dependabot (docker /docker/api) refreshes it.

FROM python:3.14-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

WORKDIR /app

# Upgrade base OS packages between digest refreshes (Trivy CRITICAL/HIGH gate:
# libpcre2 / perl-base and friends land via bookworm-security).
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends libpq5 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pip>=26.1.2" "setuptools>=78.1.1"

# Unified Backend package (includes models, Alembic migrations, and FastAPI app)
COPY backend/pyproject.toml backend/README.md backend/LICENSE /app/backend/
COPY backend/src /app/backend/src
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/

# Upgrade transitive / base tooling after package install so Trivy CRITICAL/HIGH stays green
# (msgpack via redis stack; setuptools from python:slim base).
RUN pip install --no-cache-dir /app/backend \
    && pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1" \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app

WORKDIR /app/backend/src

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
