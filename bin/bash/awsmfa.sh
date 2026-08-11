#!/bin/bash
# shellcheck disable=SC1090,SC1091

AWS_MFA_DURATION=43200
ADDRESSING_STYLE=path

usage() {
    echo "Usage: $0 [-d <aws_mfa_duration>] [-f] [-s <addressing_style>] [-b <project_path>] [-p <aws_profile>]"
    echo "  -d: Set AWS MFA duration (default: 43200 seconds)"
    echo "  -f: Force reload of MFA credentials"
    echo "  -s: Set S3 addressing style (default: path)"
    echo "  -b: Override project/repo path (default: auto-detected)"
    echo "  -p: AWS profile name"
}

_BIN_BASH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=utils.sh
source "${_BIN_BASH_DIR}/utils.sh"
PROJECT_PATH="$(resolve_repo_root)" || exit 1

while getopts ":e:d:s:p:b:fh" opt; do
    case $opt in
        d) AWS_MFA_DURATION=$OPTARG;;
        f) FORCE=1;;
        s) ADDRESSING_STYLE=$OPTARG;;
        b) PROJECT_PATH=$OPTARG;;
        h)
            usage
            exit 0
        ;;
        p) AWS_PROFILE=$OPTARG;;
        *)
            echo "$opt is not a valid option."
            usage
            exit 1
        ;;
    esac
done

if [[ ! -d "${PROJECT_PATH}" ]]; then
    log ERROR "PROJECT_PATH is not a directory: ${PROJECT_PATH}"
    exit 1
fi

POETRY_ACTIVE="${POETRY_ACTIVE:-0}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
ENV_FILE="$(resolve_papita_env_file "${PAPITA_ENV:-local}")" || exit 1
log "INFO" "Loading env vars from ${ENV_FILE}"
# shellcheck source=/dev/null
source "${ENV_FILE}"

COMMAND="aws-mfa --device ${AWS_MFA_DEVICE} --duration ${AWS_MFA_DURATION}"
if [ "${FORCE:-0}" -eq "1" ]; then
    COMMAND="${COMMAND} --force"
fi

if [ -n "${AWS_PROFILE:-}" ]; then
    COMMAND="${COMMAND} --profile ${AWS_PROFILE}"
fi

run_command 1 "${COMMAND}"

log INFO "Defining local variables..."
AWS_ACCESS_KEY_ID_="$(aws configure get aws_access_key_id --profile "${AWS_PROFILE}")"
AWS_SECRET_ACCESS_KEY_="$(aws configure get aws_secret_access_key --profile "${AWS_PROFILE}")"
AWS_SESSION_TOKEN_="$(aws configure get aws_session_token --profile "${AWS_PROFILE}")"

log INFO "Exporting variables..."
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID_}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY_}"
export AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN_}"
export AWS_S3_VERIFY=true
export AWS_S3_ADDRESSING_STYLE="${ADDRESSING_STYLE}"

log INFO "AWS-related variables successfully exported."
