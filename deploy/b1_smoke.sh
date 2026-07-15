#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# PPT-039: opt-in Supabase B1 pooler smoke. Fails loudly if the pooler gate is not met
# (unlike plain pytest, which skips so CI stays green without secrets).
#
# Default environment: staging (override with PAPITA_ENV or --env).

set -euo pipefail

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
cd "${PROJECT_PATH}"

POETRY_ACTIVE="${POETRY_ACTIVE:-0}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
PAPITA_ENV_NAME="${PAPITA_ENV:-staging}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      PAPITA_ENV_NAME="$2"
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
  log ERROR "Missing ${ENV_FILE}. Copy environments/${PAPITA_ENV}/.env.example → .env"
  exit 2
fi

log INFO "Validating B1 pooler DATABASE_URL..."
python -m poetry run python - <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path.cwd()
sys.path.insert(0, str(root / "modules" / "api" / "src"))
sys.path.insert(0, str(root / "modules" / "model" / "tests"))

from papita_txnsapi.config.environment import env_file  # noqa: E402
from postgres_gate import b1_gate_status  # noqa: E402

path = env_file()
if path.is_file():
    load_dotenv(path, override=False)

status = b1_gate_status()
print(status.message)
if not status.ok:
    print(
        "\nFix: put a Supabase *transaction pooler* URL in environments/$PAPITA_ENV/.env\n"
        "  PAPITA_ENV=staging make b1-smoke\n"
        "Local Docker (PAPITA_ENV=local) will not pass this gate — use staging/production.",
        file=sys.stderr,
    )
    raise SystemExit(2)

if not os.environ.get("JWT_SECRET_KEY"):
    print(
        "WARNING: JWT_SECRET_KEY is unset; app Settings may fail.",
        file=sys.stderr,
    )
PY

log INFO "Running modules/api/tests/test_supabase_b1_smoke.py"
python -m poetry run pytest modules/api/tests/test_supabase_b1_smoke.py -q "$@"
