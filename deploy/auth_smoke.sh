#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# PPT-039 Auth smoke: Supabase JWT → GET /api/v1/auth/me (+ optional accounts list).
#
# Requires environments/$PAPITA_ENV/.env with:
#   AUTH_PROVIDER=supabase
#   SUPABASE_URL
#   SUPABASE_ANON_KEY
#   DATABASE_URL (any Postgres the API process uses)
#
# Default environment: local (override with PAPITA_ENV or --env).
# API base URL: PAPITA_API_BASE (default http://127.0.0.1:8000)

set -euo pipefail

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
cd "${PROJECT_PATH}"

PAPITA_ENV_NAME="${PAPITA_ENV:-local}"
API_BASE="${PAPITA_API_BASE:-http://127.0.0.1:8000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      PAPITA_ENV_NAME="$2"
      shift 2
      ;;
    --base)
      API_BASE="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# shellcheck source=deploy/utils.sh
source "${PROJECT_PATH}/deploy/utils.sh"

export PAPITA_ENV="${PAPITA_ENV_NAME}"
ENV_FILE="$(resolve_papita_env_file "${PAPITA_ENV}")" || exit 1

if [[ -f "${ENV_FILE}" ]]; then
  log INFO "Loading env from ${ENV_FILE} (PAPITA_ENV=${PAPITA_ENV})"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  log ERROR "Missing env file: ${ENV_FILE}"
  exit 1
fi

if [[ "${AUTH_PROVIDER:-}" != "supabase" ]]; then
  log ERROR "AUTH_PROVIDER must be supabase for Auth smoke (got '${AUTH_PROVIDER:-unset}')."
  log ERROR "Add AUTH_PROVIDER=supabase to ${ENV_FILE}"
  exit 1
fi

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]]; then
  log ERROR "SUPABASE_URL and SUPABASE_ANON_KEY are required for Auth smoke."
  exit 1
fi

SUFFIX="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:10])')"
SMOKE_EMAIL="auth_smoke_${SUFFIX}@example.local"
SMOKE_USER="smk_${SUFFIX}"
SMOKE_PASS='SecurePass1!'

log INFO "API base: ${API_BASE}"
log INFO "Registering smoke user via API pass-through (email=${SMOKE_EMAIL})"

REG_CODE="$(
  curl -sS -o /tmp/papita_auth_smoke_reg.json -w '%{http_code}' \
    -X POST "${API_BASE}/api/v1/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${SMOKE_USER}\",\"email\":\"${SMOKE_EMAIL}\",\"password\":\"${SMOKE_PASS}\"}"
)"
if [[ "${REG_CODE}" != "201" ]]; then
  log ERROR "Register failed HTTP ${REG_CODE}: $(cat /tmp/papita_auth_smoke_reg.json)"
  exit 1
fi

log INFO "Logging in via API pass-through"
LOGIN_CODE="$(
  curl -sS -o /tmp/papita_auth_smoke_login.json -w '%{http_code}' \
    -X POST "${API_BASE}/api/v1/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "username=${SMOKE_EMAIL}&password=${SMOKE_PASS}"
)"
if [[ "${LOGIN_CODE}" != "200" ]]; then
  log ERROR "Login failed HTTP ${LOGIN_CODE}: $(cat /tmp/papita_auth_smoke_login.json)"
  exit 1
fi

TOKEN="$(python3 -c 'import json; print(json.load(open("/tmp/papita_auth_smoke_login.json"))["access_token"])')"
if [[ -z "${TOKEN}" ]]; then
  log ERROR "Login response missing access_token"
  exit 1
fi

log INFO "GET /api/v1/auth/me"
ME_CODE="$(
  curl -sS -o /tmp/papita_auth_smoke_me.json -w '%{http_code}' \
    -H "Authorization: Bearer ${TOKEN}" \
    "${API_BASE}/api/v1/auth/me"
)"
if [[ "${ME_CODE}" != "200" ]]; then
  log ERROR "/auth/me failed HTTP ${ME_CODE}: $(cat /tmp/papita_auth_smoke_me.json)"
  exit 1
fi

log INFO "GET /api/v1/accounts (tenant list)"
ACC_CODE="$(
  curl -sS -o /tmp/papita_auth_smoke_accounts.json -w '%{http_code}' \
    -H "Authorization: Bearer ${TOKEN}" \
    "${API_BASE}/api/v1/accounts"
)"
if [[ "${ACC_CODE}" != "200" ]]; then
  log ERROR "/accounts failed HTTP ${ACC_CODE}: $(cat /tmp/papita_auth_smoke_accounts.json)"
  exit 1
fi

log INFO "Auth smoke OK (me + accounts)"
python3 -c 'import json; print(json.load(open("/tmp/papita_auth_smoke_me.json")))'
exit 0
