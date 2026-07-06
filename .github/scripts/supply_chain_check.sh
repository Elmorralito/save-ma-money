#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../deploy/utils.sh
source "${PROJECT_PATH}/deploy/utils.sh"

cd "${PROJECT_PATH}" || exit

log "INFO" "Validating Poetry project and lock file..."
run_command 1 "poetry check"

log "INFO" "Validating module version metadata..."
run_command 1 "poetry run python ${PROJECT_PATH}/.github/scripts/check_module_versions.py"

log "INFO" "Supply chain metadata checks completed."
