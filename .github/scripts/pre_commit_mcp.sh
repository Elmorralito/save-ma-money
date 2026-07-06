#!/usr/bin/env bash
# Local pre-commit wrapper for MCP config validation. Skips in CI.

set -euo pipefail

if [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    exit 0
fi

export TERM="${TERM:-xterm-256color}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec /bin/bash "${SCRIPT_DIR}/mcp_config_check.sh"
