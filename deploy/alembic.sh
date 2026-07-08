#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

DOCKER_RM_FLAG=0
USE_DOCKER_FLAG=1
DB_URL=
ENV_FILE=
ALEMBIC_VERSION=
MESSAGE=
PROJECT_PATH="$(dirname "$(dirname "$(realpath "$0")")")"
ALEMBIC_PROJECT_PATH="${PROJECT_PATH}/modules/model"
DEFAULT_DB_COMPOSE_FILE="${PROJECT_PATH}/docker/database/docker-compose.yml"
DEFAULT_DB_ENV_FILE="${PROJECT_PATH}/docker/database/.env"
source "${PROJECT_PATH}/deploy/utils.sh"

usage() {
    USAGE="$(cat <<EOM
Usage: $0 ACTION [options]

PostgreSQL migration utility (Alembic via Poetry) with Docker Compose for local dev.

By default, upgrade/downgrade/version start Docker Postgres from docker/database/
unless --url or --skip-docker is set. DuckDB is not supported.

ACTIONS:
    version, autogenerate               Generate a new migration script
    upgrade, deploy                     Apply pending migrations to the database
    downgrade                           Roll back to a previous migration
    up                                  Start Docker Postgres only
    halt, stop                          Stop Docker Postgres (containers kept)
    down                                Stop and remove Docker Postgres containers

OPTIONS:
    --message, --slug, -m MESSAGE       Migration message (version/autogenerate)
    --url, -u URL                       PostgreSQL SQLAlchemy URL (skips Docker)
    --skip-docker                       Use env file DB vars; do not start Compose
    --env-file, -ef FILE                Env file (default: docker/database/.env)
    --alembic-version, --version, -av VER
                                        Downgrade target (default: head^1)
    --docker-compose-file, -dcf FILE    Compose file (default: docker/database/docker-compose.yml)
    --docker-rm, -dr                    Remove containers after migration (down, no -v)
    --docker-frm, -dfrm                 Remove containers and volumes after migration

EXAMPLES:
    $(basename "$0") up
    $(basename "$0") upgrade
    $(basename "$0") upgrade --docker-rm
    $(basename "$0") downgrade -av head^1
    $(basename "$0") upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"
    $(basename "$0") version -m "Add column" --skip-docker
    $(basename "$0") down --docker-frm

PREREQUISITES:
    - Poetry workspace installed (poetry install)
    - Docker and Docker Compose for local Postgres
    - docker/database/.env (copy DB_* vars from .env.example)
EOM
)"
    log "TRACE" "$USAGE"
    exit 1
}

get_poetry_cmd() {
    if command -v poetry &>/dev/null; then
        echo "poetry"
        return
    fi

    local python_cmd
    python_cmd=$(get_python_cmd)
    if [[ "${python_cmd}" == "python" ]]; then
        echo "python -m poetry"
    else
        echo "${python_cmd}"
    fi
}

build_alembic_exec() {
    local poetry_cmd
    poetry_cmd=$(get_poetry_cmd)
    echo "cd ${PROJECT_PATH} && ${poetry_cmd} run alembic -c ${ALEMBIC_PROJECT_PATH}/alembic.ini"
}

wait_for_postgres() {
    local attempt=0
    local max_attempts=30
    log INFO "Waiting for PostgreSQL to accept connections..."
    while [[ "${attempt}" -lt "${max_attempts}" ]]; do
        if docker compose -f "${DOCKER_COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres-db \
            sh -c 'pg_isready -U "${POSTGRES_USER:-${DB_USER:-papita}}" -d "${POSTGRES_DB:-${DB_NAME:-papita_transactions}}"' \
            &>/dev/null; then
            log INFO "PostgreSQL is ready."
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    log ERROR "PostgreSQL did not become ready within ${max_attempts}s."
    exit 1
}

docker_compose_up() {
    log INFO "Starting Docker Compose (${DOCKER_COMPOSE_FILE})..."
    run_command 1 "docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} up -d --build"
    wait_for_postgres
}

docker_compose_stop() {
    log INFO "Stopping Docker Compose services..."
    run_command 1 "docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} stop"
}

docker_compose_down() {
    local down_args="down"
    if [[ "${DOCKER_RM_FLAG}" -eq 2 ]]; then
        log INFO "Removing containers and volumes..."
        down_args="down -v"
    else
        log INFO "Removing containers..."
    fi
    run_command 1 "docker compose -f ${DOCKER_COMPOSE_FILE} --env-file ${ENV_FILE} ${down_args}"
}

run_alembic() {
    local alembic_exec
    alembic_exec=$(build_alembic_exec)
    cd "${ALEMBIC_PROJECT_PATH}" && run_command 1 "${alembic_exec} ${ALEMBIC_ARGS}"
}

run_with_docker() {
    docker_compose_up
    run_alembic
    if [[ "${DOCKER_RM_FLAG}" -gt 0 ]]; then
        docker_compose_down
    fi
}

run_without_docker() {
    run_alembic
}

POETRY_CMD=$(get_poetry_cmd)
if [[ "${POETRY_CMD}" == "poetry" ]]; then
    if ! poetry env info -p &>/dev/null; then
        log ERROR "Poetry environment not found. Run: poetry install"
        exit 1
    fi
elif ! ${POETRY_CMD} env info -p &>/dev/null; then
    log ERROR "Poetry environment not found. Run: poetry install"
    exit 1
fi

if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

ACTION="$1"
shift

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
        --docker-rm | -dr)
            DOCKER_RM_FLAG=1
            shift 1
            ;;
        --docker-frm | -dfrm)
            DOCKER_RM_FLAG=2
            shift 1
            ;;
        --skip-docker)
            USE_DOCKER_FLAG=0
            shift 1
            ;;
        --env-file | -ef)
            ENV_FILE="$2"
            shift 2
            ;;
        --message | --slug | -m)
            MESSAGE="$2"
            shift 2
            ;;
        --url | -u)
            DB_URL="$2"
            USE_DOCKER_FLAG=0
            shift 2
            ;;
        *)
            log ERROR "Unknown option: $1"
            usage
            ;;
    esac
done

DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-${DEFAULT_DB_COMPOSE_FILE}}"
ENV_FILE="${ENV_FILE:-${DEFAULT_DB_ENV_FILE}}"

if [[ "${USE_DOCKER_FLAG}" -eq 1 ]] || [[ "${ACTION}" == "up" ]] || [[ "${ACTION}" == "halt" ]] || [[ "${ACTION}" == "stop" ]] || [[ "${ACTION}" == "down" ]]; then
    if [[ ! -f "${DOCKER_COMPOSE_FILE}" ]]; then
        log ERROR "Docker Compose file not found at ${DOCKER_COMPOSE_FILE}"
        exit 1
    fi
fi

if [[ -z "${DB_URL}" ]]; then
    if [[ ! -f "${ENV_FILE}" ]]; then
        log ERROR "Env file not found at ${ENV_FILE}. Copy DB_* vars from .env.example."
        exit 1
    fi
    # shellcheck source=/dev/null
    source "${ENV_FILE}" || {
        log ERROR "Failed to load env file at ${ENV_FILE}"
        exit 1
    }
fi

ALEMBIC_ARGS=""

case "${ACTION}" in
    version | autogenerate)
        if [[ -n "${MESSAGE}" ]]; then
            MSG_ARG="-m \"${MESSAGE}\""
        else
            MSG_ARG=""
        fi
        if [[ -n "${DB_URL}" ]]; then
            ALEMBIC_ARGS="-x \"dbUrl=${DB_URL}\" revision --autogenerate ${MSG_ARG}"
        else
            ALEMBIC_ARGS="-x \"envPath=${ENV_FILE}\" revision --autogenerate ${MSG_ARG}"
        fi
        ;;
    upgrade | deploy)
        if [[ -n "${DB_URL}" ]]; then
            ALEMBIC_ARGS="-x \"dbUrl=${DB_URL}\" upgrade head"
        else
            ALEMBIC_ARGS="-x \"envPath=${ENV_FILE}\" upgrade head"
        fi
        ;;
    downgrade)
        if [[ -n "${DB_URL}" ]]; then
            ALEMBIC_ARGS="-x \"dbUrl=${DB_URL}\" downgrade ${ALEMBIC_VERSION:-head^1}"
        else
            ALEMBIC_ARGS="-x \"envPath=${ENV_FILE}\" downgrade ${ALEMBIC_VERSION:-head^1}"
        fi
        ;;
    up)
        docker_compose_up
        log INFO "Done"
        exit 0
        ;;
    halt | stop)
        docker_compose_stop
        log INFO "Done"
        exit 0
        ;;
    down)
        docker_compose_down
        log INFO "Done"
        exit 0
        ;;
    *)
        log ERROR "Action not supported: ${ACTION}"
        usage
        ;;
esac

if [[ "${USE_DOCKER_FLAG}" -eq 1 ]]; then
    log INFO "Running migrations with Docker Postgres..."
    run_with_docker
else
    log INFO "Running migrations without starting Docker..."
    run_without_docker
fi

log INFO "Done"
