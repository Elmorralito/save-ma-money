#!/usr/bin/env bash
# Export or check the committed OpenAPI artifact for modules/web (PPT-065 / #130).
# shellcheck disable=SC1091
set -euo pipefail

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

usage() {
    cat <<EOM
Usage: $(basename "$0") [--check] [--from-url URL] [--out PATH]

Export FastAPI OpenAPI JSON to modules/web/openapi/openapi.json (strategy B).

Modes:
  (default)     Offline dump via create_app().openapi() — no Compose/DB required
  --check       Fail if committed artifact drifts from a fresh offline dump
  --from-url    Optional live fetch (needs docs enabled on the running API)

Examples:
  make sync-openapi
  make check-openapi
  $(basename "$0") --from-url http://localhost:8000/api/openapi.json
EOM
    exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
fi

quoted_args=()
for arg in "$@"; do
    quoted_args+=("$(printf '%q' "${arg}")")
done

if [[ "${POETRY_ACTIVE:-0}" == "1" || -n "${VIRTUAL_ENV:-}" ]]; then
    run_command 1 "cd \"${PROJECT_PATH}\" && python \"${PROJECT_PATH}/bin/export_openapi.py\" ${quoted_args[*]-}"
else
    run_command 1 "cd \"${PROJECT_PATH}\" && poetry run python \"${PROJECT_PATH}/bin/export_openapi.py\" ${quoted_args[*]-}"
fi
