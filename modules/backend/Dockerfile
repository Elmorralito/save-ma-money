# syntax=docker/dockerfile:1
# Papita backend (FastAPI API + Alembic migrations + ingestion CLI) — one image, many commands.
# Build context: modules/backend (self-contained, like the other modules).
#   docker build -t papita-backend:local modules/backend
#
# The python:3.14-slim base tag is the reproducibility boundary; Debian security updates
# drop old package versions, so exact apt pins break rebuilds.

FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# Install into an isolated venv, upgrade patched transitive deps, and strip pip/packaging
# tooling so Trivy does not flag pip/_vendor CVEs in the runtime image.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install . \
    && /opt/venv/bin/pip install --upgrade "msgpack>=1.2.3" "urllib3>=2.8.0" \
    && /opt/venv/bin/pip uninstall -y pip \
    && rm -rf \
        /opt/venv/lib/python*/site-packages/pip* \
        /opt/venv/lib/python*/site-packages/setuptools* \
        /opt/venv/lib/python*/site-packages/wheel* \
        /opt/venv/bin/pip*

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf \
        /var/lib/apt/lists/* \
        /usr/local/lib/python*/ensurepip \
        /usr/local/lib/python*/site-packages/pip* \
        /usr/local/lib/python*/site-packages/setuptools* \
        /usr/local/lib/python*/site-packages/wheel* \
        /usr/local/bin/pip* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./

USER appuser

ENV HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live')"]

# Default: API. Override `command:` for migrations (`alembic -c alembic.ini upgrade head`)
# or ingestion (`python -m backend.domains.ingestion.cli --once`).
# Never add --reload or --workers here (single-worker runtime).
CMD ["uvicorn", "papita_txnsapi.main:app", "--host", "0.0.0.0", "--port", "8000"]
