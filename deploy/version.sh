#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
LIBS_INPUT_PATH="${PROJECT_PATH}/modules"
source "${PROJECT_PATH}/deploy/utils.sh"

MOD="${MOD:-ALL}"
VERSION="${VERSION:-prerelease}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"

usage() {
    USAGE="$(cat <<EOM
Usage: $0 [options]

Update version for module(s) using Poetry.

OPTIONS:
    --mod MODULE, -m MODULE          Module name to update (default: ALL)
                                     Valid values: ALL or module directory name
    --version VERSION, -v VERSION    Version to set (default: prerelease)
    --skip-install, --no-install     Skip poetry lock and install after version update
    --help, -h                       Show this help message

EXAMPLES:
    $0                               Update all modules to prerelease version
    $0 --mod api --version 1.0.0     Update api module to version 1.0.0
    $0 -m ALL -v patch               Update all modules to patch version
    $0 --skip-install                Update version without running poetry install
    $0 --help                        Show this help message

PREREQUISITES:
    - Poetry must be installed in your environment
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

_get_valid_modules() {
    find "${LIBS_INPUT_PATH}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || \
    find "${LIBS_INPUT_PATH}" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;
}

_validate_module() {
    if [ -z "${MOD}" ] || [ ! -d "${LIBS_INPUT_PATH}/${MOD}" ] && [ "${MOD}" != "ALL" ] ; then
        log "ERROR" "MOD is not set or the module directory does not exist"
        local valid_modules
        valid_modules="$(_get_valid_modules | tr '\n' ', ' | sed 's/, $//')"
        log "ERROR" "Valid values for MOD are: ALL, ${valid_modules}"
        return 1
    fi
    return 0
}

_prep() {
    log "INFO" "Checking Poetry installation..."
    python -m poetry env info >/dev/null 2>&1 || {
        log "INFO" "Poetry not found in environment, installing..."
        python -m pip install poetry || {
            log "ERROR" "Failed to install Poetry"
            return 1
        }
    }
    return 0
}

_lite_dev() {
    log "INFO" "Running lite-dev (poetry lock and install)..."
    cd "${PROJECT_PATH}" || {
        log "ERROR" "Failed to change directory to project root ${PROJECT_PATH}"
        return 1
    }
    python -m poetry lock || {
        log "ERROR" "Failed to run poetry lock"
        return 1
    }
    python -m poetry install || {
        log "ERROR" "Failed to run poetry install"
        return 1
    }
    return 0
}

version() {
    log "INFO" "Starting version update process..."
    log "INFO" "MOD: ${MOD}, VERSION: ${VERSION}"

    if ! _validate_module; then
        exit 1
    fi

    if ! _prep; then
        exit 1
    fi

    if [ "${MOD}" != "ALL" ]; then
        log "INFO" "Updating version for module ${MOD}..."
        cd "${LIBS_INPUT_PATH}/${MOD}" || {
            log "ERROR" "Failed to change directory to ${LIBS_INPUT_PATH}/${MOD}"
            exit 1
        }
        python -m poetry version "${VERSION}" || {
            log "ERROR" "Failed to update version for module ${MOD}"
            exit 1
        }
        cd "${PROJECT_PATH}" || {
            log "ERROR" "Failed to return to project directory"
            exit 1
        }
        if [ "${SKIP_INSTALL}" -eq 0 ]; then
            _lite_dev || exit 1
        else
            log "INFO" "Skipping poetry lock and install (--skip-install flag set)"
        fi
    else
        log "INFO" "Updating version for all modules..."
        while IFS= read -r -d '' module; do
            local module_name
            module_name="$(basename "${module}")"
            log "INFO" "Updating version for module ${module_name}..."
            cd "${module}" || {
                log "ERROR" "Failed to change directory to ${module}"
                continue
            }
            python -m poetry version "${VERSION}" || {
                log "ERROR" "Failed to update version for module ${module_name}"
                cd "${PROJECT_PATH}" || exit 1
                continue
            }
            cd "${PROJECT_PATH}" || {
                log "ERROR" "Failed to return to project directory"
                exit 1
            }
        done < <(find "${LIBS_INPUT_PATH}" -mindepth 1 -maxdepth 1 -type d -print0)
        if [ "${SKIP_INSTALL}" -eq 0 ]; then
            _lite_dev || exit 1
        else
            log "INFO" "Skipping poetry lock and install (--skip-install flag set)"
        fi
    fi

    log "INFO" "Version update process completed successfully."
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --mod | -m)
            MOD="$2"
            shift 2
            ;;
        --version | -v)
            VERSION="$2"
            shift 2
            ;;
        --skip-install | --no-install)
            SKIP_INSTALL=1
            shift
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

version
