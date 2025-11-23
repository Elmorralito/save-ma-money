#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091


PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
LIBS_INPUT_PATH="${PROJECT_PATH}/modules"
LIBS_OUTPUT_PATH="${PROJECT_PATH}/dist"
source "${PROJECT_PATH}/deploy/utils.sh"


usage() {
    USAGE="$(cat <<EOM
Usage: $0 [options]

Package the project using Poetry.

OPTIONS:
    --help, -h                           Show this help message

EXAMPLES:
    $(basename "$0")                    Package the project
    $(basename "$0") --help              Show this help message

PREREQUISITES:
    - Poetry must be installed in your environment
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

package() {
    log "INFO" "Starting package process using Poetry..."

    log "INFO" "Removing previous build artifacts..."
    rm -rf "${LIBS_OUTPUT_PATH}" ./*.whl

    while IFS= read -r -d '' lib; do
        cd "${lib}" || {
            log "ERROR" "Failed to change directory to ${lib}"
            continue
        }
        local __package_name
        __package_name="$(basename "${lib}")"
        log "INFO" "Packaging the wheel of package ${__package_name} using Poetry..."
        poetry build -f wheel -o "${LIBS_OUTPUT_PATH}" -v || {
            log "ERROR" "Failed to package the wheel."
            continue
        }
        log "INFO" "Wheel of package ${__package_name} successfully packaged at ${LIBS_OUTPUT_PATH}"
    done <    <(find "${LIBS_INPUT_PATH}" -depth 1 -type d -print0)

    cd "${PROJECT_PATH}" && log "INFO" "Package process completed successfully."
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --help | -h)
            usage
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
done

package "$@"
