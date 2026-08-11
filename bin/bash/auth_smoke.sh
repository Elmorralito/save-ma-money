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

_BIN_BASH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=utils.sh
source "${_BIN_BASH_DIR}/utils.sh"
PROJECT_PATH="$(resolve_repo_root)" || exit 1
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
# Supabase Auth rejects .local / example.* test domains and rate-limits default SMTP.
# Prefer a real domain you control (or set AUTH_SMOKE_EMAIL to a full address).
if [[ -n "${AUTH_SMOKE_EMAIL:-}" ]]; then
  SMOKE_EMAIL="${AUTH_SMOKE_EMAIL}"
  SMOKE_USER="${AUTH_SMOKE_USERNAME:-smk_${SUFFIX}}"
else
  SMOKE_DOMAIN="${AUTH_SMOKE_EMAIL_DOMAIN:-}"
  if [[ -z "${SMOKE_DOMAIN}" ]]; then
    log ERROR "Set AUTH_SMOKE_EMAIL or AUTH_SMOKE_EMAIL_DOMAIN in ${ENV_FILE}."
    log ERROR "Supabase rejects test domains (e.g. example.com / .local)."
    log ERROR "Also disable Auth → Providers → Email → Confirm email for local smoke,"
    log ERROR "or configure custom SMTP (default SMTP is rate-limited)."
    exit 1
  fi
  SMOKE_EMAIL="auth_smoke_${SUFFIX}@${SMOKE_DOMAIN}"
  SMOKE_USER="smk_${SUFFIX}"
fi
SMOKE_PASS="${AUTH_SMOKE_PASSWORD:-SecurePass1!}"

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
if [[ "${ACC_CODE}" == "404" ]]; then
  log ERROR "/accounts returned 404 — the API at ${API_BASE} does not expose domain routers."
  log ERROR "OpenAPI on that process often only has health/auth/budgets (stale uvicorn/docker image)."
  log ERROR "Rebuild/restart the Compose API, then re-run make auth-smoke:"
  log ERROR "  make api-up"
  log ERROR "Or: make stack-up"
  exit 1
fi
if [[ "${ACC_CODE}" != "200" ]]; then
  log ERROR "/accounts failed HTTP ${ACC_CODE}: $(cat /tmp/papita_auth_smoke_accounts.json)"
  exit 1
fi

log INFO "Auth smoke OK (me + accounts)"
python3 -c 'import json; print(json.load(open("/tmp/papita_auth_smoke_me.json")))'
exit 0
