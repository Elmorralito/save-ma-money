#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
LIBS_INPUT_PATH="${PROJECT_PATH}/modules"
LIBS_OUTPUT_PATH="${PROJECT_PATH}/dist"
source "${PROJECT_PATH}/bin/utils.sh"

MOD="${MOD:-ALL}"

usage() {
    USAGE="$(cat <<EOM
Usage: $0 [options]

Build Poetry sdist + wheel artifacts into dist/ (repo root).

OPTIONS:
    --mod MODULE, -m MODULE   Module directory under modules/ (default: ALL)
                              Example: --mod model  (papita-transactions-model only)
    --help, -h                Show this help message

EXAMPLES:
    $(basename "$0")                 Build all modules under modules/
    $(basename "$0") --mod model     Build papita-transactions-model only (PPT-024)
    MOD=model $(basename "$0")       Same via env

PREREQUISITES:
    - Poetry must be installed in your environment
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

_get_valid_modules() {
    find "${LIBS_INPUT_PATH}" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;
}

_validate_module() {
    if [ -z "${MOD}" ] || { [ "${MOD}" != "ALL" ] && [ ! -d "${LIBS_INPUT_PATH}/${MOD}" ]; }; then
        log "ERROR" "MOD is not set or the module directory does not exist: ${MOD:-<empty>}"
        local valid_modules
        valid_modules="$(_get_valid_modules | tr '\n' ',' | sed 's/,$//')"
        log "ERROR" "Valid values for MOD are: ALL, ${valid_modules}"
        return 1
    fi
    return 0
}

_modules_to_build() {
    if [ "${MOD}" = "ALL" ]; then
        find "${LIBS_INPUT_PATH}" -mindepth 1 -maxdepth 1 -type d -print
        return 0
    fi
    printf '%s\n' "${LIBS_INPUT_PATH}/${MOD}"
}

package() {
    log "INFO" "Starting package process using Poetry (MOD=${MOD})..."

    if ! _validate_module; then
        exit 1
    fi

    log "INFO" "Removing previous build artifacts in ${LIBS_OUTPUT_PATH}..."
    rm -rf "${LIBS_OUTPUT_PATH}"
    mkdir -p "${LIBS_OUTPUT_PATH}"

    local lib
    local __package_name
    local failed=0
    while IFS= read -r lib; do
        [ -n "${lib}" ] || continue
        cd "${lib}" || {
            log "ERROR" "Failed to change directory to ${lib}"
            failed=1
            continue
        }
        __package_name="$(basename "${lib}")"
        log "INFO" "Building sdist + wheel for ${__package_name}..."
        if ! python -m poetry build -o "${LIBS_OUTPUT_PATH}" -v; then
            log "ERROR" "Failed to package ${__package_name}."
            failed=1
            continue
        fi
        log "INFO" "Artifacts for ${__package_name} written to ${LIBS_OUTPUT_PATH}"
    done < <(_modules_to_build)

    cd "${PROJECT_PATH}" || exit 1
    if [ "${failed}" -ne 0 ]; then
        log "ERROR" "Package process completed with errors."
        exit 1
    fi
    log "INFO" "Package process completed successfully."
    ls -la "${LIBS_OUTPUT_PATH}" || true
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --mod | -m)
            MOD="${2:-}"
            shift 2
            ;;
        --help | -h)
            usage
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
done

package
