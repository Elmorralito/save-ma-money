#!/usr/bin/env bash
# Local Docker Compose stack wrapper (replaces the old Makefile targets).
#
#   ./deploy/scripts/deploy-dev.sh up [--build] [--profile NAME] [SERVICE...]
#   ./deploy/scripts/deploy-dev.sh down
#   ./deploy/scripts/deploy-dev.sh logs [SERVICE...]
#   ./deploy/scripts/deploy-dev.sh wait          # block until the API answers /health/live
#
# Reads environments/local/.env (copy from environments/local/.env.example).
# An exported ALLOWED_ORIGINS in the shell would override --env-file, so it is unset.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-environments/local/.env}"
COMPOSE=(env -u ALLOWED_ORIGINS docker compose --env-file "${ENV_FILE}" -f compose.yaml)

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

require_docker() {
  docker info >/dev/null 2>&1 || {
    echo "Docker is not running. Start Docker, then retry." >&2
    exit 1
  }
}

wait_for_api() {
  local port
  port="$(grep -E '^API_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || true)"
  port="${port:-8000}"
  echo "Waiting for API on :${port}..."
  for _ in $(seq 1 60); do
    if curl -sf "http://localhost:${port}/api/v1/health/live" >/dev/null 2>&1; then
      echo "API ready: http://localhost:${port}/api/docs"
      return 0
    fi
    sleep 2
  done
  echo "API did not become healthy in time. Try: ${COMPOSE[*]} logs api" >&2
  return 1
}

action="${1:-}"
[[ -n "${action}" ]] || usage
shift

case "${action}" in
  up)
    require_docker
    "${COMPOSE[@]}" up -d "$@"
    if [[ "$*" != *ingestor* ]]; then
      wait_for_api
    fi
    ;;
  down)
    require_docker
    "${COMPOSE[@]}" down "$@"
    ;;
  logs)
    "${COMPOSE[@]}" logs -f "$@"
    ;;
  wait)
    wait_for_api
    ;;
  *)
    usage
    ;;
esac
