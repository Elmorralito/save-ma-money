#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# PPT-061 / #126: deterministic E2E seed against a running B0 Compose API.
#
# Usage:
#   make api-all
#   make web-e2e-seed              # idempotent upsert
#   make web-e2e-seed RESET=1      # soft-delete baseline txns + E2E accounts; categories reused
#
# Env (optional):
#   E2E_API_BASE, E2E_USER_EMAIL, E2E_USER_PASSWORD, E2E_USER_USERNAME
#   E2E_SEED_OUT, E2E_SKIP_REGISTER=1 (pre-provisioned Supabase user)

set -euo pipefail

_BIN_BASH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=utils.sh
source "${_BIN_BASH_DIR}/utils.sh"
PROJECT_PATH="$(resolve_repo_root)" || exit 1
cd "${PROJECT_PATH}"

PAPITA_ENV_NAME="${PAPITA_ENV:-local}"
RESET_FLAG="${RESET:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      PAPITA_ENV_NAME="$2"
      shift 2
      ;;
    --reset)
      RESET_FLAG="1"
      shift
      ;;
    --api-base)
      export E2E_API_BASE="$2"
      shift 2
      ;;
    --out)
      export E2E_SEED_OUT="$2"
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
fi

# Prefer Compose publish port when E2E_API_BASE is unset.
if [[ -z "${E2E_API_BASE:-}" ]]; then
  API_PORT="$(grep -E '^API_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || true)"
  API_PORT="${API_PORT:-8000}"
  export E2E_API_BASE="http://127.0.0.1:${API_PORT}"
fi

ARGS=(python3 "${PROJECT_PATH}/bin/python/web_e2e_seed.py" --api-base "${E2E_API_BASE}")
if [[ "${RESET_FLAG}" == "1" ]]; then
  ARGS+=(--reset)
  log INFO "RESET=1 — soft-deleting baseline txns + E2E accounts (categories reused)"
fi
if [[ -n "${E2E_SEED_OUT:-}" ]]; then
  ARGS+=(--out "${E2E_SEED_OUT}")
fi

log INFO "Seeding E2E fixtures against ${E2E_API_BASE}"
"${ARGS[@]}"
