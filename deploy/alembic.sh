#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

DOCKER_RM_FLAG=
DOCKER_LOCAL_FLAG=
DUCKDB_DB_PATH=
ENV_FILE=
DUCKDB_SCHEMA="papita_transactions"
PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
ALEMBIC_EXEC_COMMAND="alembic"
ALEMBIC_PROJECT_PATH="${PROJECT_PATH}/modules/model"
DEFAULT_DB_COMPOSE_FILE="${PROJECT_PATH}/docker/database/docker-compose.yml"
DEFAULT_DB_ENV_FILE="${PROJECT_PATH}/docker/database/.env"
source "${PROJECT_PATH}/deploy/utils.sh"

usage() {
    USAGE="$(cat <<EOM
Usage: $0 ACTION [options]

Database migration utility for Alembic with optional Docker integration.

The script loads environment variables from docker/database/.env by default.

ACTIONS:
    version, autogenerate               Generate a new migration script
    upgrade                             Apply pending migrations to the database
    downgrade                           Roll back to a previous migration
    up                                  Start the Docker services for migration environment
    halt, stop                          Stop the Docker services for migration environment
    down                                Destroy the Docker services for migration environment

OPTIONS:
    --message, --slug, -m MESSAGE           Specify a message for the migration
                                            (used with version/autogenerate)
    --env-file, -ef FILE                    Specify a custom environment file path
                                            (defaults to docker/database/.env)
    --duckdb-db-path, -dbp PATH             Specify a DuckDB database path. Supports:
                                                - DuckDB protocol: duckdb:///path or duckdb://path
                                                - POSIX paths: /absolute/path.db, ./relative.db,
                                                    ../relative.db, or path/to/file.db
                                                - In-memory: :memory: or duckdb:///:memory:
                                            When provided, operations use DuckDB instead of Docker
    --duckdb-schema, -ds SCHEMA             Specify the DuckDB schema name
                                            (defaults to papita_transactions)
    --alembic-version, --version, -av VER   Specify version to downgrade to
                                            (defaults to head^1)
    --docker-compose-file, -dcf FILE        Specify a custom Docker Compose file path
                                            (defaults to docker/database/docker-compose.yml)
    --docker-local, -dl                     Run with Docker services (starts containers)
    --docker-rm, -dr                        Remove Docker containers after execution
    --docker-frm, -dfrm                     Force remove containers AND volumes after execution

EXAMPLES:
    $(basename "$0") version -m "Add users table"
    $(basename "$0") upgrade --docker-local --docker-rm
    $(basename "$0") downgrade -av abc123
    $(basename "$0") upgrade --duckdb-db-path /path/to/duckdb.db
    $(basename "$0") upgrade --duckdb-db-path ./data/store.duckdb --duckdb-schema my_schema
    $(basename "$0") version -m "New migration" --duckdb-db-path duckdb:///path/to/db.db
    $(basename "$0") down --docker-frm

PREREQUISITES:
    - Alembic must be installed in your environment
    - Docker and Docker Compose (if using Docker functionality)
    - Python and Poetry (for DuckDB operations)
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

docker_run() {
    if [[ "$DOCKER_LOCAL_FLAG" -eq 1 ]]; then
        DOCKER_COMMAND="docker compose -f $DOCKER_COMPOSE_FILE --env-file $ENV_FILE up -d --build"
        run_command 1 "$DOCKER_COMMAND"
        log INFO "Waiting 5 seconds for the database to start..."
        sleep 5
    fi

    cd "$ALEMBIC_PROJECT_PATH" && run_command 0 "$ALEMBIC_COMMAND"

    if [[ "$DOCKER_LOCAL_FLAG" -eq 2 ]] && [[ "$DOCKER_RM_FLAG" -eq 0 ]] && [ -n "$DOCKER_COMPOSE_FILE" ]; then
        log INFO "Stoping local database..."
        DOCKER_COMMAND="docker compose -f $DOCKER_COMPOSE_FILE --env-file $ENV_FILE stop"
        run_command 1 "$DOCKER_COMMAND"
    fi

    if [[ "$DOCKER_LOCAL_FLAG" -eq 1 ]] && [[ "$DOCKER_RM_FLAG" -gt 0 ]] && [ -n "$DOCKER_COMPOSE_FILE" ]; then
        log INFO "Destroying local database..."
        DOCKER_COMMAND="docker compose -f $DOCKER_COMPOSE_FILE --env-file $ENV_FILE down"
        [[ "$DOCKER_RM_FLAG" -eq 2 ]] && {
            log INFO "Destroying database's volume as well..."
            DOCKER_COMMAND="${DOCKER_COMMAND} -v"
        }
        run_command 1 "$DOCKER_COMMAND"
    fi
}

duckdb_run() {
    log "INFO" "Running DuckDB with database path: $DUCKDB_DB_PATH"
    # shellcheck disable=SC2001
    DUCKDB_DB_PATH="$(echo "$DUCKDB_DB_PATH" | sed -e 's|^duckdb://||')"
    if [[ "$DUCKDB_DB_PATH" == ":memory:" ]]; then
        log ERROR "DuckDB database path must be :memory: or a valid path."
        usage
    fi

    python "${PROJECT_PATH}/deploy/setup_duckdb.py" -path "$DUCKDB_DB_PATH" -schema "$DUCKDB_SCHEMA" || {
        log ERROR "Failed to setup DuckDB schema."
        exit 1
    }
    run_command 0 "$ALEMBIC_COMMAND" ;
    cd - || return
}

if ! test -e "$(which "$ALEMBIC_EXEC_COMMAND")" && ! test -e "$(python -m poetry env info -p)"; then
    log "ERROR" "The environment does not have Alembic nor Poetry installed."
    exit 1
fi

ALEMBIC_EXEC_COMMAND="cd $PROJECT_PATH ; python -m poetry run alembic -c ${ALEMBIC_PROJECT_PATH}/alembic.ini"

# Show usage if no arguments or help requested
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

ACTION="$1"
shift

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --alembic-version | --version | -av)
            ALEMBIC_VERSION="$2"
            shift 2
            ;;
        --docker-compose-file | -dcf)
            DOCKER_COMPOSE_FILE="$2"
            shift 2
            ;;
        --docker-local | -dl)
            DOCKER_LOCAL_FLAG=1
            RUN_FLAG="docker_run"
            shift 1
            ;;
        --docker-rm | -dr)
            DOCKER_RM_FLAG=1
            RUN_FLAG="docker_run"
            shift 1
            ;;
        --docker-frm | -dfrm)
            DOCKER_RM_FLAG=2
            RUN_FLAG="docker_run"
            shift 1
            ;;
        --duckdb-db-path | -dbp)
            DUCKDB_DB_PATH="$2"
            shift 2
            ;;
        --duckdb-schema | -ds)
            DUCKDB_SCHEMA="$2"
            shift 2
            ;;
        --env-file | -ef)
            ENV_FILE="$2"
            shift 2
            ;;
        --message | --slug | -m)
            MESSAGE="$2"
            shift 2
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
done

DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-"${DEFAULT_DB_COMPOSE_FILE}"}"
ENV_FILE="${ENV_FILE:-"${DEFAULT_DB_ENV_FILE}"}"

log "INFO" "Using Docker Compose file at $DOCKER_COMPOSE_FILE"
if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
    log "ERROR" "Docker Compose file not found at $DOCKER_COMPOSE_FILE"
    exit 1
fi

log "INFO" "Using env file at $ENV_FILE"
if [[ ! -f "$ENV_FILE" ]]; then
    log "ERROR" "Env file not found at $ENV_FILE"
    exit 1
fi

log "INFO" "Loading env file at $ENV_FILE"
source "${ENV_FILE}" || {
    log "ERROR" "Failed to load env file at $ENV_FILE"
    exit 1
}

case "$ACTION" in
    version | autogenerate)
        if [[ -n "$DUCKDB_DB_PATH" ]]; then
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"duckdbPath=${DUCKDB_DB_PATH}\" revision --autogenerate $( if [ -n "$MESSAGE" ] ; then echo "-m \"${MESSAGE}\"" ; else echo "" ; fi )"
        else
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"envPath=${ENV_FILE}\" revision --autogenerate $( if [ -n "$MESSAGE" ] ; then echo "-m \"${MESSAGE}\"" ; else echo "" ; fi )"
        fi
        ;;
    upgrade)
        if [[ -n "$DUCKDB_DB_PATH" ]]; then
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"duckdbPath=${DUCKDB_DB_PATH}\" upgrade head"
        else
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"envPath=${ENV_FILE}\" upgrade head"
        fi
        ;;
    downgrade)
        if [[ -n "$DUCKDB_DB_PATH" ]]; then
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"duckdbPath=${DUCKDB_DB_PATH}\" upgrade ${ALEMBIC_VERSION:-"head^1"}"
        else
            ALEMBIC_COMMAND="$ALEMBIC_EXEC_COMMAND -x \"envPath=${ENV_FILE}\" upgrade ${ALEMBIC_VERSION:-"head^1"}"
        fi
        ;;
    up)
        ALEMBIC_COMMAND="echo 'Bringing up the local services...'"
        DOCKER_RM_FLAG=0
        DOCKER_LOCAL_FLAG=1
        RUN_FLAG="docker_run"
        ;;
    halt | stop)
        ALEMBIC_COMMAND="echo 'Stopping the local services...'"
        DOCKER_RM_FLAG=0
        DOCKER_LOCAL_FLAG=2
        RUN_FLAG="docker_run"
        ;;
    down)
        ALEMBIC_COMMAND="echo 'Bringing down the local services...'"
        DOCKER_LOCAL_FLAG=1
        RUN_FLAG="docker_run"
        ;;
    *)
        log "ERROR" "Action not supported."
        usage
        ;;
esac

if [[ -n "$DUCKDB_DB_PATH" ]]; then
    log "INFO" "Using DuckDB database path: $DUCKDB_DB_PATH"
    RUN_FLAG="duckdb_run"
fi

log "INFO" "Running action: $RUN_FLAG"
eval "$RUN_FLAG"

log "INFO" "Done"
