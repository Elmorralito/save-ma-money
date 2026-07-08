#!/usr/bin/env bash
# Local pre-push wrapper for CI adoption scoring. Advisory only — never blocks push.

set -euo pipefail

if [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}" || exit 0

if [[ -z "${REPO_NAME:-}" ]]; then
    remote_url="$(git config --get remote.origin.url 2>/dev/null || true)"
    if [[ "${remote_url}" =~ github\.com[:/]([^/]+/[^/.]+) ]]; then
        export REPO_NAME="${BASH_REMATCH[1]}"
    else
        export REPO_NAME="owner/repo"
    fi
fi

python "${SCRIPT_DIR}/evaluate_ci.py" || true
exit 0
