# Papita web SPA — multi-stage: pnpm build → nginx:alpine (PPT-057 / #122)
# Build context: repository root
#   docker build -f docker/web/Dockerfile --build-arg VITE_APP_TITLE=Papita .
#
# Public VITE_* values are baked at image build time (not runtime env on nginx).

# -----------------------------------------------------------------------------
# Stage 1: production bundle
# -----------------------------------------------------------------------------
FROM node:22-bookworm-slim AS build

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
# Stage 2: static nginx
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine

COPY docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/modules/web/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
