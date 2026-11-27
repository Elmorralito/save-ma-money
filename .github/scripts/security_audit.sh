#!/usr/bin/env bash
# Unified local & CI security audit gate for save-ma-money.
# Usage:
#   ./.github/scripts/security_audit.sh          # fast gate (security tests + SAST + web security)
#   ./.github/scripts/security_audit.sh --full   # also runs pip-audit + pnpm audit
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

FULL_MODE=0
if [[ "${1:-}" == "--full" ]]; then
  FULL_MODE=1
fi

log() {
  printf '[security-audit] %s\n' "$1"
}

log "1/3 Running backend security hardening & Gmail hardening tests..."
poetry run pytest \
  modules/backend/tests/api/test_api_security_hardening.py \
  modules/backend/tests/api/test_ingestion.py \
  modules/backend/tests/api/test_ingestion_schemas.py \
  modules/backend/tests/ingestor_email/test_gmail_security_hardening.py

log "2/3 Running Python SAST (ruff flake8-bandit / bandit) on security-critical paths..."
SAST_TARGETS=(
  modules/backend/src/papita_txnsapi/middleware/
  modules/backend/src/papita_ingestor_email/parsers/security.py
  modules/backend/src/papita_ingestor_email/parsers/mime.py
  modules/backend/src/papita_ingestor_email/sources/gmail.py
)
if poetry run python -c "import ruff" 2>/dev/null || command -v ruff >/dev/null 2>&1; then
  (poetry run ruff check --select S "${SAST_TARGETS[@]}" 2>/dev/null || ruff check --select S "${SAST_TARGETS[@]}")
elif poetry run python -c "import bandit" 2>/dev/null; then
  poetry run bandit -q -r "${SAST_TARGETS[@]}"
else
  log "NOTE: ruff/bandit not installed in local venv; run in CI or install ruff for SAST."
fi

log "3/3 Running web auth security unit tests..."
(cd modules/web && ./node_modules/.bin/vitest run src/api/auth.security.test.ts)

if [[ "${FULL_MODE}" -eq 1 ]]; then
  log "Running full dependency vulnerability audits (pip-audit + pnpm audit)..."
  /bin/bash .github/scripts/supply_chain_check.sh
  pnpm audit --prod --audit-level=high
fi

log "All security audit checks passed."
