#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../bin/utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

cd "${PROJECT_PATH}" || exit

log "INFO" "Validating Poetry project metadata..."
run_command 1 "poetry check"

log "INFO" "Validating module version metadata..."
run_command 1 "poetry run python ${PROJECT_PATH}/.github/scripts/check_module_versions.py"

log "INFO" "Upgrading pip to a patched release..."
run_command 1 "poetry run python -m pip install --disable-pip-version-check --upgrade 'pip>=26.1.2'"

log "INFO" "Auditing installed dependencies..."
run_command 1 "poetry run python -m pip install --disable-pip-version-check pip-audit"
run_command 1 "poetry run pip-audit --desc on --skip-editable"

log "INFO" "Supply chain checks completed."
