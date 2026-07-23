#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# Ensure monthly transaction partitions exist and drop partitions older than retention.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

cd "${ROOT_DIR}"
DATABASE_URL="${DATABASE_URL:-${DB_URL:-}}"
if [[ -z "${DATABASE_URL}" ]]; then
  echo "DATABASE_URL or DB_URL must be set." >&2
  exit 1
fi
export DATABASE_URL

poetry run python - <<'PY'
import json
import os

from papita_txnsmodel.config.transaction_partitions import run_partition_maintenance

database_url = os.environ["DATABASE_URL"]
result = run_partition_maintenance(database_url=database_url)
print(json.dumps(result, indent=2))
PY
