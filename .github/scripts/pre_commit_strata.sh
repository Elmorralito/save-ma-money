#!/usr/bin/env bash
# Local pre-commit wrapper for Strata validation. Skips in CI (quality-control runs pre-commit too).

set -euo pipefail

if [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    exit 0
fi

export TERM="${TERM:-xterm-256color}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export STRATA_STRICT_MODULES=1
export STRATA_DIFF_SOURCE=staged

exec /bin/bash "${SCRIPT_DIR}/strata_check.sh"
