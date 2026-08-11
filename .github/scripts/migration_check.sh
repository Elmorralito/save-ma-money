#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

# shellcheck source=../../bin/bash/utils.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../bin/bash" && pwd)/utils.sh"
PROJECT_PATH="$(resolve_repo_root)" || exit 1

ALEMBIC_INI="${PROJECT_PATH}/modules/model/alembic.ini"
ALEMBIC_CMD="cd ${PROJECT_PATH} && poetry run alembic -c ${ALEMBIC_INI}"

usage() {
    cat <<EOM
Usage: $(basename "$0")

Run Alembic migration checks for CI against PostgreSQL.

ENVIRONMENT:
    DB_URL      PostgreSQL SQLAlchemy URL (required)
EOM
    exit 1
}

if [[ -z "${DB_URL:-}" ]]; then
    log "ERROR" "DB_URL is required for PostgreSQL migration checks."
    usage
fi

log "INFO" "Running PostgreSQL migration upgrade to head..."
run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" upgrade head"

log "INFO" "Running PostgreSQL migration downgrade one revision..."
run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" downgrade -1"

log "INFO" "Re-applying PostgreSQL migration upgrade to head..."
run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" upgrade head"

log "INFO" "Running alembic check for model drift..."
run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" check"

log "INFO" "PostgreSQL migration checks completed."
