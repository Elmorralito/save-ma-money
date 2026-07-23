#!/usr/bin/env bash
# Run pre-commit quality hooks on changed Python and Bash files (Strata strict mode).
# Invoked from strata_check.sh when STRATA_CODE_REVIEW=1 (default in strict mode).

# shellcheck disable=SC1090,SC1091
set -euo pipefail

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../bin/utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

cd "${PROJECT_PATH}" || exit 1

STRATA_CODE_REVIEW="${STRATA_CODE_REVIEW:-1}"
FAIL=0

fail() {
    log "ERROR" "$1"
    FAIL=1
}

ok() {
    log "INFO" "$1"
}

is_reviewable_path() {
    local path="$1"
    if [[ "${path}" == modules/* ]]; then
        [[ "${path}" == *.py ]] && return 0
    fi
    if [[ "${path}" == bin/* ]]; then
        [[ "${path}" == *.py || "${path}" == *.sh ]] && return 0
    fi
    if [[ "${path}" == .github/scripts/* ]]; then
        [[ "${path}" == *.py || "${path}" == *.sh ]] && return 0
    fi
    return 1
}

if [[ "${STRATA_CODE_REVIEW}" != "1" ]]; then
    ok "Strata code review skipped (STRATA_CODE_REVIEW=${STRATA_CODE_REVIEW})"
    exit 0
fi

CHANGED_FILES="${1:-}"
if [[ -z "${CHANGED_FILES}" ]]; then
    ok "Strata code review skipped — no changed paths in diff"
    exit 0
fi

PY_FILES=()
SH_FILES=()
while IFS= read -r path; do
    [[ -z "${path}" ]] && continue
    if [[ ! -f "${PROJECT_PATH}/${path}" ]]; then
        continue
    fi
    if ! is_reviewable_path "${path}"; then
        continue
    fi
    if [[ "${path}" == *.py ]]; then
        PY_FILES+=("${path}")
    elif [[ "${path}" == *.sh ]]; then
        SH_FILES+=("${path}")
    fi
done <<< "${CHANGED_FILES}"

if [[ ${#PY_FILES[@]} -eq 0 && ${#SH_FILES[@]} -eq 0 ]]; then
    ok "Strata code review skipped — no reviewable Python or Bash files in diff"
    exit 0
fi

if ! command -v poetry >/dev/null 2>&1; then
    fail "poetry not found — install Poetry to run Strata code review locally"
    exit 1
fi

run_hook_on_files() {
    local hook="$1"
    shift
    local files=("$@")
    if [[ ${#files[@]} -eq 0 ]]; then
        return 0
    fi
    log "INFO" "Strata code review: pre-commit ${hook} on ${#files[@]} file(s)"
    if ! poetry run pre-commit run "${hook}" --files "${files[@]}"; then
        fail "Strata code review failed: pre-commit ${hook}"
    fi
}

PYTHON_HOOKS=(black isort flake8 pylint mypy)
if [[ ${#PY_FILES[@]} -gt 0 ]]; then
    for hook in "${PYTHON_HOOKS[@]}"; do
        run_hook_on_files "${hook}" "${PY_FILES[@]}"
    done
fi

if [[ ${#SH_FILES[@]} -gt 0 ]]; then
    run_hook_on_files shellcheck "${SH_FILES[@]}"
fi

if [[ "${FAIL}" -eq 0 ]]; then
    ok "Strata code review passed (${#PY_FILES[@]} Python, ${#SH_FILES[@]} Bash)"
    exit 0
fi

log "ERROR" "Strata code review failed — fix lint/format issues or run: pre-commit run --files <paths>"
exit 1
