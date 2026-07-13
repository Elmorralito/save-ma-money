#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
# Validate .strata/ layout and integrity for belousov-petr/strata layout_version 3.
# Does not run /strata:save — enforces structure and frontmatter only.

set -euo pipefail

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../deploy/utils.sh
source "${PROJECT_PATH}/deploy/utils.sh"

cd "${PROJECT_PATH}" || exit 1

STRATA_DIR="${PROJECT_PATH}/.strata"
AGENTS_ADAPTER="${PROJECT_PATH}/.agents/AGENTS.md"
CLAUDE_ADAPTER="${PROJECT_PATH}/.agents/CLAUDE.md"
FAIL=0
STRICT_MODULES="${STRATA_STRICT_MODULES:-0}"

fail() {
    log "ERROR" "$1"
    FAIL=1
}

ok() {
    log "INFO" "$1"
}

require_file() {
    if [[ -f "$1" ]]; then
        ok "present: ${1#"${PROJECT_PATH}/"}"
    else
        fail "missing required file: ${1#"${PROJECT_PATH}/"}"
    fi
}

require_dir() {
    if [[ -d "$1" ]]; then
        ok "present: ${1#"${PROJECT_PATH}/"}/"
    else
        fail "missing required directory: ${1#"${PROJECT_PATH}/"}/"
    fi
}

log "INFO" "Validating Strata layout (layout_version 3)..."

if [[ ! -d "${STRATA_DIR}" ]]; then
    fail ".strata/ directory not found — run strata init or commit the scaffold"
    echo
    if [[ "${FAIL}" -eq 0 ]]; then
        log "INFO" "Strata checks passed."
    else
        log "ERROR" "Strata checks failed."
        exit 1
    fi
    exit 1
fi

require_file "${STRATA_DIR}/MANIFEST.md"
require_file "${AGENTS_ADAPTER}"
require_file "${CLAUDE_ADAPTER}"

for rel in \
    memory/MEMORY.md \
    memory/project_state.md \
    memory/learnings/INDEX.md \
    memory/learnings/_TEMPLATE.md \
    memory/archive/ARCHIVE.md \
    memory/archive/action_log.md \
    issues/README.md \
    issues/_TEMPLATE.md \
    issues/ACTIVE.md \
    issues/OPEN.md \
    issues/PARKED.md \
    docs/ARCHITECTURE.md \
    inbox/.gitignore; do
    require_file "${STRATA_DIR}/${rel}"
done

for rel in \
    memory/learnings \
    memory/archive \
    issues/archive \
    docs/product \
    docs/architecture \
    docs/decisions \
    docs/reference \
    docs/ops \
    inbox; do
    require_dir "${STRATA_DIR}/${rel}"
done

if grep -q "^layout_version: 3$" "${STRATA_DIR}/MANIFEST.md"; then
    ok "MANIFEST.md declares layout_version: 3"
else
    fail "MANIFEST.md missing layout_version: 3 frontmatter stamp"
fi

if grep -qF ".strata/MANIFEST.md" "${AGENTS_ADAPTER}" "${CLAUDE_ADAPTER}"; then
    ok ".agents/AGENTS.md and .agents/CLAUDE.md reference .strata/MANIFEST.md"
else
    fail ".agents/AGENTS.md or .agents/CLAUDE.md does not reference .strata/MANIFEST.md"
fi

if grep -rE '\{\{(PROJECT_NAME|INIT_DATE)\}\}' "${STRATA_DIR}" "${AGENTS_ADAPTER}" "${CLAUDE_ADAPTER}" >/dev/null 2>&1; then
    fail "unsubstituted Strata template placeholders remain under .strata/ or adapters"
    grep -rnE '\{\{(PROJECT_NAME|INIT_DATE)\}\}' "${STRATA_DIR}" "${AGENTS_ADAPTER}" "${CLAUDE_ADAPTER}" || true
else
    ok "no unsubstituted template placeholders"
fi

memory_lines=$(wc -l < "${STRATA_DIR}/memory/MEMORY.md" | tr -d ' ')
if [[ "${memory_lines}" -le 80 ]]; then
    ok "memory/MEMORY.md within budget (${memory_lines}/80 lines)"
else
    fail "memory/MEMORY.md exceeds 80-line hot budget (${memory_lines} lines)"
fi

state_lines=$(wc -l < "${STRATA_DIR}/memory/project_state.md" | tr -d ' ')
if [[ "${state_lines}" -le 200 ]]; then
    ok "memory/project_state.md within budget (${state_lines}/200 lines)"
else
    fail "memory/project_state.md exceeds 200-line budget (${state_lines} lines)"
fi

VALID_TYPES="bug|improvement|debt|task|feature|initiative"
VALID_STATUSES="open|in-progress|parked|resolved|wont-fix"
VALID_SEVERITY="high|med|low"

issue_count=0
while IFS= read -r -d '' issue_file; do
    issue_count=$((issue_count + 1))
    rel_path="${issue_file#"${PROJECT_PATH}/"}"

    if ! grep -q '^---$' "${issue_file}"; then
        fail "${rel_path}: missing YAML frontmatter"
        continue
    fi

    issue_type=$(awk '/^---$/{f=!f; next} f && /^type:/{sub(/^type:[[:space:]]*/,""); print; exit}' "${issue_file}")
    issue_status=$(awk '/^---$/{f=!f; next} f && /^status:/{sub(/^status:[[:space:]]*/,""); print; exit}' "${issue_file}")
    issue_severity=$(awk '/^---$/{f=!f; next} f && /^severity:/{sub(/^severity:[[:space:]]*/,""); print; exit}' "${issue_file}")

    if [[ -z "${issue_type}" ]] || ! echo "${issue_type}" | grep -qE "^(${VALID_TYPES})$"; then
        fail "${rel_path}: invalid or missing type '${issue_type}'"
    fi
    if [[ -z "${issue_status}" ]] || ! echo "${issue_status}" | grep -qE "^(${VALID_STATUSES})$"; then
        fail "${rel_path}: invalid or missing status '${issue_status}'"
    fi
    if [[ -n "${issue_severity}" ]] && ! echo "${issue_severity}" | grep -qE "^(${VALID_SEVERITY})$"; then
        fail "${rel_path}: invalid severity '${issue_severity}'"
    fi
    if [[ "${issue_status}" == "parked" ]] && ! grep -qE '^revive-when:' "${issue_file}"; then
        fail "${rel_path}: parked items require revive-when frontmatter"
    fi
done < <(find "${STRATA_DIR}/issues" -maxdepth 1 -type f -name '[0-9]*-*.md' -print0)

if [[ "${issue_count}" -eq 0 ]]; then
    ok "no issue item files yet (views-only backlog is valid at init)"
else
    ok "validated ${issue_count} issue item file(s)"
fi

if [[ "${STRICT_MODULES}" == "1" ]]; then
    log "INFO" "Strict mode: checking .strata/ updates alongside code changes..."
    if [[ "${STRATA_DIFF_SOURCE:-range}" == "staged" ]]; then
        changed_files=$(git diff --cached --name-only 2>/dev/null || true)
    else
        base_ref="${STRATA_BASE_REF:-origin/main}"
        if git rev-parse --verify "${base_ref}" >/dev/null 2>&1; then
            changed_files=$(git diff --name-only "${base_ref}...HEAD" 2>/dev/null || git diff --name-only "${base_ref}" HEAD)
        else
            changed_files=""
            log "INFO" "Skipping strict pairing — base ref '${base_ref}' not available locally"
        fi
    fi

    if [[ -n "${changed_files}" ]]; then
        needs_strata_pairing=false
        strata_changed=false
        while IFS= read -r path; do
            [[ -z "${path}" ]] && continue
            if [[ "${path}" == .strata/* ]] || [[ "${path}" == .agents/* ]] || [[ "${path}" == .cursor/AGENTS.md ]] || [[ "${path}" == .cursor/CLAUDE.md ]]; then
                strata_changed=true
            elif [[ "${path}" == "pyproject.toml" ]] || [[ "${path}" =~ ^modules/[^/]+/pyproject\.toml$ ]]; then
                : # dependency manifest-only edits (e.g. Dependabot) do not require memory updates
            elif [[ "${path}" == modules/* ]] || [[ "${path}" == deploy/* ]]; then
                needs_strata_pairing=true
            fi
        done <<< "${changed_files}"

        if [[ "${needs_strata_pairing}" == true ]] && [[ "${strata_changed}" == false ]]; then
            fail "code paths changed but .strata/ (or .agents/** / .cursor/AGENTS.md / .cursor/CLAUDE.md) was not updated — run /strata:save, restage, and retry"
        elif [[ "${needs_strata_pairing}" == true ]]; then
            ok "strict code/strata change pairing satisfied"
        else
            ok "strict pairing skipped — no architecture code paths in diff"
        fi

        if [[ "${STRATA_CODE_REVIEW:-1}" == "1" ]]; then
            log "INFO" "Strict mode: reviewing changed Python and Bash files..."
            if ! /bin/bash "${SCRIPT_DIR}/strata_code_review.sh" "${changed_files}"; then
                fail "Strata code review failed on changed Python or Bash files"
            fi
        else
            ok "Strata code review skipped (STRATA_CODE_REVIEW=${STRATA_CODE_REVIEW:-0})"
        fi
    elif [[ "${STRATA_DIFF_SOURCE:-range}" == "staged" ]]; then
        ok "strict pairing skipped — no staged paths (nothing in index)"
    else
        ok "strict pairing skipped — no diff vs ${STRATA_BASE_REF:-origin/main} (branch matches base or no commits yet)"
    fi
fi

echo
if [[ "${FAIL}" -eq 0 ]]; then
    log "INFO" "Strata checks passed."
    exit 0
fi

log "ERROR" "Strata checks failed."
exit 1
