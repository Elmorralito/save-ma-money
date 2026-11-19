#!/usr/bin/env bash
# Validate workspace metadata and audit installed dependencies.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

log() {
  printf '%s %s\n' "$1" "$2"
}

log "INFO" "Validating Poetry project metadata..."
poetry check

log "INFO" "Validating workspace and module metadata..."
poetry run python "${ROOT}/.github/scripts/check_module_versions.py"

log "INFO" "Auditing installed dependencies..."
poetry run python -m pip install --disable-pip-version-check --quiet pip-audit
poetry run pip-audit --desc on --skip-editable

log "INFO" "Supply chain checks completed."
