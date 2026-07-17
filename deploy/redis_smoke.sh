#!/usr/bin/env bash
# Smoke Redis wiring against a running Papita API (PPT-043).
#
# Prerequisites:
#   - API up (make stack-up, or host uvicorn with REDIS_ENABLED=true)
#   - Redis reachable (Compose redis service or managed URL)
#
# Usage:
#   make redis-smoke
#   API_BASE_URL=http://localhost:8000 ./deploy/redis_smoke.sh

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "==> Redis smoke against ${API_BASE_URL}"

ready="$(curl -fsS "${API_BASE_URL}/api/v1/health/ready")"
echo "ready: ${ready}"
echo "${ready}" | grep -Eq '"ready"[[:space:]]*:[[:space:]]*true'

redis_health="$(curl -fsS "${API_BASE_URL}/api/v1/health/redis")"
echo "redis: ${redis_health}"
echo "${redis_health}" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"'
echo "${redis_health}" | grep -Fq 'api-redis link healthy'

composite="$(curl -fsS "${API_BASE_URL}/api/v1/health")"
echo "health: ${composite}"
echo "${composite}" | grep -Eq '"redis"[[:space:]]*:[[:space:]]*"connected"'

echo "OK — Redis is wired and ready"
