#!/bin/bash
# Shared helpers for bin/bash/* and .github/scripts/*.
#
# Bootstrap from a sibling script under bin/bash/:
#   _BIN_BASH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
#   # shellcheck source=utils.sh
#   source "${_BIN_BASH_DIR}/utils.sh"
#   PROJECT_PATH="$(resolve_repo_root)" || exit 1

GREEN_TEXT='\033[0;32m'
RED_TEXT='\033[0;31m'
NC_TEXT='\033[0m'
export TERM="${TERM:-"xterm-256color"}"
if tput bold &>/dev/null; then
    BOLD_TEXT="$(tput bold)"
    NORMAL_TEXT="$(tput sgr0)"
else
    BOLD_TEXT=""
    NORMAL_TEXT=""
fi

log() {
    local level="$1"
    shift
    local color="${NC_TEXT}"
    if [[ "${level}" == "ERROR" ]]; then
        color="${RED_TEXT}"
    elif [[ "${level}" == "INFO" ]]; then
        color="${GREEN_TEXT}"
    elif [[ "$level" == "TRACE" ]]; then
        echo -e "$*"
        return
    fi
    echo -e "${color}$(date +"%Y-%m-%d %H:%M:%S") :: ${BOLD_TEXT}$(basename "$0")${NORMAL_TEXT} ${color}:: ${BOLD_TEXT}${level}${NORMAL_TEXT} ${color}:: $*${NC_TEXT}"
}


get_python_cmd() {
    if [[ "${POETRY_ACTIVE:-0}" == "1" ]] || [[ -n "${VIRTUAL_ENV:-}" ]]; then
        echo "python"
    else
        echo "python -m poetry"
    fi
}

# Locate monorepo root (directory with pyproject.toml + modules/).
# Walks upward from this file so callers stay correct if bin/ deepens again.
resolve_repo_root() {
    local dir
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    while [[ "${dir}" != "/" ]]; do
        if [[ -f "${dir}/pyproject.toml" && -d "${dir}/modules" ]]; then
            printf '%s\n' "${dir}"
            return 0
        fi
        dir="$(dirname "${dir}")"
    done
    log ERROR "Could not locate repo root (pyproject.toml + modules/) from ${BASH_SOURCE[0]}"
    return 1
}

# Resolve environments/<PAPITA_ENV>/.env (default local). Optional override: first arg.
# Usage: resolve_papita_env_file [name]  → prints absolute path; exits 1 on unknown name.
resolve_papita_env_file() {
    local name="${1:-${PAPITA_ENV:-local}}"
    local root
    root="$(resolve_repo_root)" || return 1
    case "${name}" in
        local | staging | production) ;;
        *)
            log ERROR "Unknown PAPITA_ENV='${name}' (expected local|staging|production)"
            return 1
            ;;
    esac
    echo "${root}/environments/${name}/.env"
}


run_command() {
    COMMAND="$2"
    EXIT_ON_ERROR="$1"
    log INFO "Running command:"
    log TRACE "$COMMAND"
    $SHELL -c "$COMMAND"
    RESULT=$?
    if [[ "$RESULT" -ne "0" ]]; then
        log ERROR "Command failed."
        if [[ "$EXIT_ON_ERROR" -eq "1" ]]; then
            log ERROR "Exiting with status ${RESULT}."
            exit "$RESULT"
        fi
    else
        log INFO "Command succeeded."
    fi
}


sso_login() {
    log "INFO" "Checking if SSO login..."
    if [ -z "${AWS_PROFILE:-}" ] || [ -z "${SSO_LOGIN:-}" ] || ! command -v aws &>/dev/null ; then
        log "INFO" "Skipping SSO login as AWS_PROFILE or SSO_LOGIN is not set."
        return
    fi
    log "INFO" "Checking if the session is still valid."
    aws sts --profile "$AWS_PROFILE" get-caller-identity > /dev/null 2>&1 || {
        log "INFO" "Logging in with profile '$AWS_PROFILE'..."
        aws sso login --profile "$AWS_PROFILE" || {
            log "ERROR" "Profile ${AWS_PROFILE} does not exist."
            exit 1
        }
    }

    log "INFO" "Defining AWS environment variables..."
    AWS_ACCESS_KEY_ID_="$(aws configure get aws_access_key_id --profile "$AWS_PROFILE")"
    AWS_SECRET_ACCESS_KEY_="$(aws configure get aws_secret_access_key --profile "$AWS_PROFILE")"
    AWS_SESSION_TOKEN_="$(aws configure get aws_session_token --profile "$AWS_PROFILE")"

    log "INFO" "Exporting AWS environment variables..."
    export AWS_PROFILE="$AWS_PROFILE"
    export AWS_REGION="$AWS_REGION"
    export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID_"
    export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY_"
    export AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN_"
}
