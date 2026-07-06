#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../deploy/utils.sh
source "${PROJECT_PATH}/deploy/utils.sh"

ALEMBIC_INI="${PROJECT_PATH}/modules/model/alembic.ini"
ALEMBIC_CMD="cd ${PROJECT_PATH} && poetry run alembic -c ${ALEMBIC_INI}"
DUCKDB_SEED_REVISION="93420bed0a90"

usage() {
    cat <<EOM
Usage: $(basename "$0") DIALECT

Run Alembic migration checks for CI.

DIALECT:
    postgres    Apply full migration chain on PostgreSQL (upgrade, downgrade, upgrade, check)
    duckdb      Smoke-test initial seed migration on DuckDB

ENVIRONMENT (postgres):
    DB_URL      PostgreSQL SQLAlchemy URL (required)

ENVIRONMENT (duckdb):
    DUCKDB_FILE Optional DuckDB file path (default: /tmp/papita_migration_ci.duckdb)
EOM
    exit 1
}

prepare_duckdb_url() {
    local duckdb_file="${1:-/tmp/papita_migration_ci.duckdb}"
    rm -f "${duckdb_file}"
    poetry run python "${PROJECT_PATH}/deploy/setup_duckdb.py" \
        -path "${duckdb_file}" \
        -schema papita_transactions
}

run_postgres_checks() {
    if [[ -z "${DB_URL:-}" ]]; then
        log "ERROR" "DB_URL is required for postgres migration checks."
        exit 1
    fi

    log "INFO" "Running PostgreSQL migration upgrade to head..."
    run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" upgrade head"

    log "INFO" "Running PostgreSQL migration downgrade one revision..."
    run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" downgrade -1"

    log "INFO" "Re-applying PostgreSQL migration upgrade to head..."
    run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" upgrade head"

    log "INFO" "Running alembic check for model drift..."
    run_command 1 "${ALEMBIC_CMD} -x \"dbUrl=${DB_URL}\" check"
}

run_duckdb_checks() {
    local duckdb_file="${DUCKDB_FILE:-/tmp/papita_migration_ci.duckdb}"
    local duckdb_url

    log "INFO" "Preparing DuckDB database at ${duckdb_file}..."
    duckdb_url="$(prepare_duckdb_url "${duckdb_file}")"

    log "INFO" "Running DuckDB smoke migration to seed revision ${DUCKDB_SEED_REVISION}..."
    log "INFO" "Full incremental migrations on DuckDB are not CI-gated (ALTER COLUMN limitations)."
    run_command 1 "${ALEMBIC_CMD} -x \"duckdbPath=${duckdb_url}\" upgrade ${DUCKDB_SEED_REVISION}"
}

if [[ $# -ne 1 ]]; then
    usage
fi

DIALECT="$1"
case "${DIALECT}" in
    postgres)
        run_postgres_checks
        ;;
    duckdb)
        run_duckdb_checks
        ;;
    *)
        log "ERROR" "Unknown dialect: ${DIALECT}"
        usage
        ;;
esac

log "INFO" "Migration checks completed for ${DIALECT}."
