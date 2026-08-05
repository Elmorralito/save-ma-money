# Papita web SPA - multi-stage: pnpm build -> nginx (PPT-057 / #122 + PPT-063 / #128)
# Build context: repository root
#   docker build -f docker/web/Dockerfile --build-arg VITE_APP_TITLE=Papita .
#
# Public VITE_* values are baked at image build time (not runtime env on nginx).
# Final stage runs as non-root (Trivy DS-0002) on port 8080.

# -----------------------------------------------------------------------------
# Stage 1: production bundle
# -----------------------------------------------------------------------------
FROM node:25-bookworm-slim AS build

WORKDIR /app

RUN corepack enable \
    && corepack prepare pnpm@9.15.9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .nvmrc ./
COPY modules/web/package.json ./modules/web/

RUN pnpm install --frozen-lockfile --filter @papita/web...

COPY modules/web ./modules/web

# Bake-time public env only (never secrets / service-role keys)
ARG VITE_APP_TITLE=Papita
ARG VITE_PAPITA_BREAKING_CHANGES_ID=ppt-044
# Empty = same-origin relative /api (nginx proxy). Do not point at :8000 in Compose.
ARG VITE_API_BASE_URL=

ENV VITE_APP_TITLE=${VITE_APP_TITLE} \
    VITE_PAPITA_BREAKING_CHANGES_ID=${VITE_PAPITA_BREAKING_CHANGES_ID} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN pnpm --filter @papita/web build

# -----------------------------------------------------------------------------
# Stage 2: static nginx (non-root)
# -----------------------------------------------------------------------------
# Base digest pinned for supply-chain stability; Dependabot (docker /docker/web) refreshes it.
# 1.27-alpine carried fixed Alpine HIGH/CRITICAL (openssl/musl/zlib); keep current mainline.
FROM nginxinc/nginx-unprivileged:1.31.3-alpine@sha256:a6c3ec0c0d249d68b0682df854d4a9e222b90fb607dc3fcf2f1d2fcbc85d347e

# Apply Alpine security patches between base rebuilds (Trivy CRITICAL/HIGH gate).
USER root
RUN apk upgrade --no-cache

# .inc is not auto-loaded by conf.d/*.conf; included from default.conf (PPT-063 / #128).
COPY docker/web/spa-security-headers.conf /etc/nginx/conf.d/spa-security-headers.inc
COPY docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/modules/web/dist /usr/share/nginx/html

# Explicit non-root USER for Trivy DS-0002 (base image also defaults to nginx/101)
USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
