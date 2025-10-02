#!/bin/bash

GREEN_TEXT='\033[0;32m'
RED_TEXT='\033[0;31m'
NC_TEXT='\033[0m'
export TERM="${TERM:-"xterm-256color"}"
BOLD_TEXT="$(tput bold)"
NORMAL_TEXT="$(tput sgr0)"

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
