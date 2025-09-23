#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
source "${PROJECT_PATH}/deploy/utils.sh"

usage() {
    USAGE="$(cat <<EOM
Usage: $0 [options]

Test runner utility for running pytest tests.

The script runs pytest tests for the project.

OPTIONS:
    --log, -l                           Enable logging of test output to a file
    --tests-results-path, -trp PATH     Specify a custom path for test results
                                        (defaults to '.tmp')

EXAMPLES:
    $(basename "$0")                    Run tests without logging
    $(basename "$0") --log              Run tests with logging enabled
    $(basename "$0") -trp /path/to/file Run tests with custom output path

PREREQUISITES:
    - pytest must be installed in your environment
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

test -e "$(which pytest)" || {
    log "ERROR" "Pytest not found."
    usage
}

ENABLE_LOGS=
TESTS_RESULTS_PATH=".tmp"

# Show usage if help requested
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --log | -l)
            ENABLE_LOGS="1"
            shift
            ;;
        --tests-results-path | -trp)
            TESTS_RESULTS_PATH="$2"
            shift 2
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ "$ENABLE_LOGS" -eq "1" ]] ; then
    mkdir -p "$TESTS_RESULTS_PATH"
fi

TEST_COMMAND="pytest -vs . $( if [[ "$ENABLE_LOGS" -eq 1 ]] ; then echo "> ${TESTS_RESULTS_PATH}.$(basename "$PROJECT_PATH").log" ; else echo "" ; fi )"
run_command 0 "$TEST_COMMAND"

rm -rf "duckdb:" "MagickMock/getcwd()"
log "INFO" "Done"
