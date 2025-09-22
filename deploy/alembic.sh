#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
source "${PROJECT_PATH}/deploy/utils.sh"

usage() {
   USAGE="$(cat <<EOM
Usage: $0 ACTION [options]

Database migration utility for Alembic with optional Docker integration.

The script loads environment variables from transactions-model/.env by default.

ACTIONS:
    version, autogenerate               Generate a new migration script
    upgrade, migrate                    Apply pending migrations to the database
    downgrade                           Roll back to a previous migration
    up                                  Start the Docker services for migration environment
    down                                Stop the Docker services for migration environment

OPTIONS:
    --message, --slug, -m MESSAGE       Specify a message for the migration
                                        (used with version/autogenerate)
    --env-file, -e FILE                 Specify a custom environment file path
    --alembic-version, --version VER    Specify version to downgrade to
                                        (defaults to previous version)
    --compose-file, -f FILE             Specify a custom Docker Compose file path
    --local                             Run with Docker services (starts containers)
    --rm                                Remove Docker containers after execution
    --frm                               Force remove containers AND volumes after execution

EXAMPLES:
    $(basename "$0") version -m "Add users table"
    $(basename "$0") upgrade
    $(basename "$0") downgrade --alembic-version abc123
    $(basename "$0") upgrade --local --rm
    $(basename "$0") down --frm

PRERREQUISITES:
    - Alembic must be installed in your environment
    - Docker and Docker Compose (if using Docker functionality)
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

test -e "$(which alembic)" || {
    log "ERROR" "Alembic not found."
    usage
}

RM_FLAG=
LOCAL_FLAG=
ALEMBIC_PATH="${PROJECT_PATH}/papita-transactions-model"
ENV_FILE="${ALEMBIC_PATH}/.env"

# Show usage if no arguments or help requested
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

ACTION="$1"
shift

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --message | --slug | -m)
            MESSAGE="$2"
            shift 2
            ;;
        --env-file | -e)
            ENV_FILE="$2"
            shift 2
            ;;
        --alembic-version | --version)
            ALEMBIC_VERSION="$2"
            shift 2
            ;;
        --compose-file | -f)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --local)
            LOCAL_FLAG=1
            shift 1
            ;;
        --rm)
            RM_FLAG=1
            shift 1
            ;;
        --frm)
            RM_FLAG=2
            shift 1
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
done

log "INFO" "Loading env file at $ENV_FILE"
source "${ENV_FILE}" || {
    log "ERROR" "Failed to load env file at $ENV_FILE"
    exit 1
}

case "$ACTION" in
    version | autogenerate)
        ALEMBIC_COMMAND="alembic revision --autogenerate $( if [ -n "$MESSAGE" ] ; then echo "-m \"${MESSAGE}\"" ; else echo "" ; fi )"
        ;;
    upgrade | migrate)
        ALEMBIC_COMMAND="alembic upgrade head"
        ;;
    downgrade)
        ALEMBIC_COMMAND="alembic upgrade ${ALEMBIC_VERSION:-"head^1"}"
        ;;
    up)
        ALEMBIC_COMMAND="echo 'Bringing up the services...'"
        RM_FLAG=0
        LOCAL_FLAG=1
        ;;
    down)
        ALEMBIC_COMMAND="echo 'Bringing down the services...'"
        if [[ "$RM_FLAG" -eq 0 ]] ; then RM_FLAG=1 ; fi
        LOCAL_FLAG=1
        ;;
    *)
        log "ERROR" "Action not supported."
        usage
        ;;
esac

if [[ "$LOCAL_FLAG" -eq 1 ]]; then
    COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_PATH}/docker/alembic.yml}"
    DOCKER_COMMAND="docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build"
    run_command 1 "$DOCKER_COMMAND"
    log INFO "Waiting 5 seconds for the database to start..."
    sleep 5
fi

cd "$ALEMBIC_PATH" && run_command 0 "$ALEMBIC_COMMAND"

if [[ "$LOCAL_FLAG" -eq 1 ]] && [[ "$RM_FLAG" -gt 0 ]] && [ -n "$COMPOSE_FILE" ]; then
    DOCKER_COMMAND="docker compose -f $COMPOSE_FILE --env-file $ENV_FILE down"
    DOCKER_COMMAND="${DOCKER_COMMAND}$( if [[ "$RM_FLAG" -eq 2 ]] ; then echo " -v" ; else echo "" ; fi )"
    run_command 1 "$DOCKER_COMMAND"
fi

log "INFO" "Done"
