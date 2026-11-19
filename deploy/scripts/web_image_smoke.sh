#!/usr/bin/env bash
# Smoke-test a papita web nginx image: GET / + SPA security headers (PPT-063).
# Usage: web_image_smoke.sh <image:tag> [host_port]
# PPT-067 — used by publish-web-image.yml (build-smoke + pre-push).

set -euo pipefail

IMAGE_TAG="${1:-}"
HOST_PORT="${2:-18080}"
CONTAINER_NAME="${WEB_IMAGE_SMOKE_NAME:-papita-web-ci}"

if [[ -z "${IMAGE_TAG}" ]]; then
  echo "usage: $0 <image:tag> [host_port]" >&2
  exit 2
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d --name "${CONTAINER_NAME}" -p "${HOST_PORT}:8080" "${IMAGE_TAG}"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${HOST_PORT}/" >/dev/null; then
    break
  fi
  sleep 1
done

curl -sf "http://127.0.0.1:${HOST_PORT}/" >/dev/null
HDRS="$(curl -sI "http://127.0.0.1:${HOST_PORT}/")"
echo "${HDRS}"
echo "${HDRS}" | grep -qi '^content-security-policy:'
echo "${HDRS}" | grep -F "script-src 'self'" >/dev/null
echo "${HDRS}" | grep -F "frame-ancestors 'none'" >/dev/null
echo "${HDRS}" | grep -qi '^x-content-type-options: *nosniff'
echo "${HDRS}" | grep -qi '^referrer-policy: *no-referrer'
echo "${HDRS}" | grep -qi '^x-frame-options: *DENY'
echo "Web SPA header smoke OK (${IMAGE_TAG})"
