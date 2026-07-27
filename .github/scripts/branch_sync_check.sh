#!/usr/bin/env bash
# Fail when HEAD is behind the sync base (default: origin/main).
# Ahead-of-base feature commits are expected and do not fail the check.
#
# Usage:
#   /bin/bash .github/scripts/branch_sync_check.sh
#   BASE_REF=origin/main /bin/bash .github/scripts/branch_sync_check.sh
# shellcheck disable=SC1090,SC1091

set -euo pipefail

PROJECT_PATH="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"
# shellcheck source=../../bin/utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

BASE_REF="${BASE_REF:-origin/main}"
HEAD_REF="${HEAD_REF:-HEAD}"

if ! git rev-parse --verify "${BASE_REF}" >/dev/null 2>&1; then
    log "ERROR" "Base ref not found: ${BASE_REF} (fetch main first: git fetch origin main)"
    exit 1
fi

if ! git rev-parse --verify "${HEAD_REF}" >/dev/null 2>&1; then
    log "ERROR" "Head ref not found: ${HEAD_REF}"
    exit 1
fi

behind="$(git rev-list --count "${HEAD_REF}..${BASE_REF}")"
ahead="$(git rev-list --count "${BASE_REF}..${HEAD_REF}")"
merge_base="$(git merge-base "${HEAD_REF}" "${BASE_REF}")"

log "INFO" "sync check: head=${HEAD_REF} base=${BASE_REF}"
log "INFO" "merge-base=${merge_base}"
log "INFO" "behind=${behind} ahead=${ahead}"

if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    {
        echo "## Branch sync with main"
        echo ""
        echo "| | |"
        echo "| :--- | :--- |"
        echo "| Head | \`${HEAD_REF}\` |"
        echo "| Base | \`${BASE_REF}\` |"
        echo "| Merge-base | \`${merge_base}\` |"
        echo "| Behind base | ${behind} |"
        echo "| Ahead of base | ${ahead} |"
    } >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
fi

if [[ "${behind}" -gt 0 ]]; then
    log "ERROR" "Branch is ${behind} commit(s) behind ${BASE_REF}."
    log "ERROR" "Merge or rebase main, then push — e.g. git fetch origin && git merge origin/main"
    if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
        echo "::error::Branch is ${behind} commit(s) behind ${BASE_REF}. Merge or rebase main before merging this PR."
    fi
    exit 1
fi

log "INFO" "Branch is not behind ${BASE_REF} (in sync for merge purposes)."
exit 0
