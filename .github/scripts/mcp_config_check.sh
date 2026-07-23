#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# Validate project .cursor/mcp.json for Cursor MCP server configuration.

set -euo pipefail

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../bin/utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

cd "${PROJECT_PATH}" || exit 1

MCP_FILE="${PROJECT_PATH}/.cursor/mcp.json"
FAIL=0

fail() {
    log "ERROR" "$1"
    FAIL=1
}

ok() {
    log "INFO" "$1"
}

if [[ ! -f "${MCP_FILE}" ]]; then
    ok "no project .cursor/mcp.json — skipping MCP validation"
    exit 0
fi

log "INFO" "Validating .cursor/mcp.json..."

if ! python3 -m json.tool "${MCP_FILE}" >/dev/null 2>&1; then
    fail ".cursor/mcp.json is not valid JSON"
fi

if [[ "${FAIL}" -eq 0 ]]; then
    ok ".cursor/mcp.json is valid JSON"
fi

if [[ "${FAIL}" -eq 0 ]]; then
    if ! python3 <<'PY' "${MCP_FILE}"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

if not isinstance(data, dict):
    raise SystemExit("root must be a JSON object")

servers = data.get("mcpServers")
if servers is None:
    print("ok: mcpServers omitted (empty config)")
    raise SystemExit(0)

if not isinstance(servers, dict):
    raise SystemExit("mcpServers must be a JSON object")

for name, cfg in servers.items():
    if not isinstance(cfg, dict):
        raise SystemExit(f"mcpServers.{name} must be a JSON object")
    has_url = isinstance(cfg.get("url"), str) and bool(cfg.get("url", "").strip())
    has_command = isinstance(cfg.get("command"), str) and bool(cfg.get("command", "").strip())
    if not has_url and not has_command:
        raise SystemExit(f"mcpServers.{name} must define a non-empty url or command")

print(f"ok: validated {len(servers)} MCP server(s)")
PY
    then
        fail "MCP config structure validation failed"
    else
        ok "MCP server entries have url or command"
    fi
fi

# Reject obvious secret material in committed MCP config (names only in env refs are fine).
if grep -qE '(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{10,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})' "${MCP_FILE}"; then
    fail ".cursor/mcp.json appears to contain a hardcoded token or API key — use env vars or Cursor secrets"
else
    ok "no obvious hardcoded tokens in .cursor/mcp.json"
fi

echo
if [[ "${FAIL}" -eq 0 ]]; then
    log "INFO" "MCP config checks passed."
    exit 0
fi

log "ERROR" "MCP config checks failed."
exit 1
