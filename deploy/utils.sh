#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local color="${NC}"
    if [[ "${level}" == "ERROR" ]]; then
        color="${RED}"
    elif [[ "${level}" == "INFO" ]]; then
        color="${GREEN}"
    fi
    echo -e "${color}$(date +"%Y-%m-%d %H:%M:%S") ${0}::${level}::$*${NC}"
}

run_command() {
    COMMAND="$2"
    EXIT_ON_ERROR="$1"
    log INFO "Running command:"
    echo "${COMMAND}"
    $SHELL -c "${COMMAND}"
    RESULT=$?
    if [[ "$RESULT" -ne "0" ]]; then
        log ERROR "Command failed."
        if [[ "${EXIT_ON_ERROR}" -eq "1" ]]; then
            log ERROR "Exiting with status ${RESULT}."
            exit "${RESULT}"
        fi
    else
        log INFO "Command succeeded."
    fi
}
