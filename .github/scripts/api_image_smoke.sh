#!/usr/bin/env bash
# Smoke-test a papita API image: GET /api/v1/health/live must return alive=true.
# Usage: api_image_smoke.sh <image:tag> [host_port]
# PPT-067 / #132 — used by publish-api-image.yml (PR build-smoke + post-publish).

set -euo pipefail

IMAGE_TAG="${1:-}"
HOST_PORT="${2:-18000}"
CONTAINER_NAME="${API_IMAGE_SMOKE_NAME:-papita-api-ci}"

if [[ -z "${IMAGE_TAG}" ]]; then
  echo "usage: $0 <image:tag> [host_port]" >&2
  exit 2
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d --name "${CONTAINER_NAME}" -p "${HOST_PORT}:8000" \
  -e AUTH_PROVIDER=local \
  -e REDIS_ENABLED=false \
  -e DEBUG=true \
  -e DOCS_ENABLED=false \
  -e JWT_SECRET_KEY="ci-smoke-only-replace-me-min-32-chars" \
  "${IMAGE_TAG}"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${HOST_PORT}/api/v1/health/live" >/dev/null; then
    break
  fi
  sleep 1
done

curl -sf "http://127.0.0.1:${HOST_PORT}/api/v1/health/live" | tee /tmp/papita-api-live.json
grep -q '"alive"[[:space:]]*:[[:space:]]*true' /tmp/papita-api-live.json
echo "API liveness smoke OK (${IMAGE_TAG})"
