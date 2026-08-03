#!/usr/bin/env bash
# Wait until all GitHub Actions workflow runs for a commit SHA have concluded
# successfully (or were skipped), excluding this publish workflow itself.
#
# Always requires a core set of PR workflows to have appeared (avoids racing
# ahead before Quality Control / Secret Scan / Branch sync register).
#
# Concurrent PR re-triggers (concurrency cancel-in-progress, labeled/unlabeled)
# leave superseded runs as conclusion=cancelled — those are ignored, not failures.
#
# Usage:
#   COMMIT_SHA=<sha> /bin/bash .github/scripts/wait_for_pr_checks.sh
#
# Env:
#   COMMIT_SHA              Required. Commit to inspect.
#   EXCLUDE_WORKFLOW_NAME   Workflow name to ignore (default: Publish model (dev)).
#   REQUIRED_WORKFLOWS      Comma-separated names that must succeed
#                           (default: Secret Scan,Branch sync with main,Code Quality Control).
#   TIMEOUT_SECONDS         Max wait (default: 2700).
#   POLL_SECONDS            Poll interval (default: 30).
#   INITIAL_GRACE_SECONDS   Sleep before first evaluation (default: 45).
#   REPO                    owner/repo (default: $GITHUB_REPOSITORY).
# shellcheck disable=SC1090,SC1091

set -euo pipefail

PROJECT_PATH="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"
# shellcheck source=../../bin/utils.sh
source "${PROJECT_PATH}/bin/utils.sh"

COMMIT_SHA="${COMMIT_SHA:-}"
EXCLUDE_WORKFLOW_NAME="${EXCLUDE_WORKFLOW_NAME:-Publish model (dev)}"
REQUIRED_WORKFLOWS="${REQUIRED_WORKFLOWS:-Secret Scan,Branch sync with main,Code Quality Control}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-2700}"
POLL_SECONDS="${POLL_SECONDS:-30}"
INITIAL_GRACE_SECONDS="${INITIAL_GRACE_SECONDS:-45}"
REPO="${REPO:-${GITHUB_REPOSITORY:-}}"

if [[ -z "${COMMIT_SHA}" ]]; then
    log "ERROR" "COMMIT_SHA is required"
    exit 1
fi

if [[ -z "${REPO}" ]]; then
    log "ERROR" "REPO or GITHUB_REPOSITORY is required"
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    log "ERROR" "gh CLI is required"
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    log "ERROR" "jq is required"
    exit 1
fi

IFS=',' read -r -a REQUIRED_LIST <<<"${REQUIRED_WORKFLOWS}"
# trim whitespace around names
for i in "${!REQUIRED_LIST[@]}"; do
    REQUIRED_LIST[i]="$(echo "${REQUIRED_LIST[i]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
done

deadline=$((SECONDS + TIMEOUT_SECONDS))
log "INFO" "Waiting for checks on ${COMMIT_SHA}"
log "INFO" "exclude='${EXCLUDE_WORKFLOW_NAME}' required='${REQUIRED_WORKFLOWS}' timeout=${TIMEOUT_SECONDS}s"

if [[ "${INITIAL_GRACE_SECONDS}" -gt 0 ]]; then
    log "INFO" "Initial grace ${INITIAL_GRACE_SECONDS}s (let PR workflows register)"
    sleep "${INITIAL_GRACE_SECONDS}"
fi

while ((SECONDS < deadline)); do
    mapfile -t runs_json < <(
        gh api --paginate "repos/${REPO}/actions/runs?head_sha=${COMMIT_SHA}&per_page=100" \
            --jq '.workflow_runs[] | @json'
    )

    if [[ "${#runs_json[@]}" -eq 0 ]]; then
        log "INFO" "No workflow runs yet for ${COMMIT_SHA}; sleeping ${POLL_SECONDS}s"
        sleep "${POLL_SECONDS}"
        continue
    fi

    pending=0
    failed=0
    considered=0
    ignored_cancelled=0
    unset conclusions_by_name summaries 2>/dev/null || true
    declare -A conclusions_by_name
    declare -a summaries

    for row in "${runs_json[@]}"; do
        name="$(jq -r '.name' <<<"${row}")"
        status="$(jq -r '.status' <<<"${row}")"
        conclusion="$(jq -r '.conclusion // empty' <<<"${row}")"
        event="$(jq -r '.event' <<<"${row}")"
        html_url="$(jq -r '.html_url' <<<"${row}")"

        if [[ "${name}" == "${EXCLUDE_WORKFLOW_NAME}" ]]; then
            continue
        fi

        # Only gate on pull_request runs for this head SHA.
        if [[ "${event}" != "pull_request" && "${event}" != "pull_request_target" ]]; then
            continue
        fi

        # Superseded by concurrency cancel-in-progress (or a newer labeled/synchronize run).
        if [[ "${status}" == "completed" && "${conclusion}" == "cancelled" ]]; then
            ignored_cancelled=$((ignored_cancelled + 1))
            continue
        fi

        considered=$((considered + 1))
        summaries+=("${name}|${status}|${conclusion:-<none>}|${html_url}")

        if [[ "${status}" != "completed" ]]; then
            pending=$((pending + 1))
            conclusions_by_name["${name}"]="pending"
            continue
        fi

        conclusions_by_name["${name}"]="${conclusion}"

        case "${conclusion}" in
            success | skipped | neutral)
                ;;
            *)
                failed=$((failed + 1))
                log "ERROR" "Failing check: ${name} conclusion=${conclusion} ${html_url}"
                ;;
        esac
    done

    missing_required=0
    for req in "${REQUIRED_LIST[@]}"; do
        [[ -n "${req}" ]] || continue
        if [[ -z "${conclusions_by_name[${req}]+x}" ]]; then
            missing_required=$((missing_required + 1))
            log "INFO" "Required workflow not registered yet: ${req}"
            continue
        fi
        case "${conclusions_by_name[${req}]}" in
            success | skipped | neutral)
                ;;
            pending)
                log "INFO" "Required workflow still pending: ${req}"
                ;;
            *)
                failed=$((failed + 1))
                log "ERROR" "Required workflow failed: ${req} conclusion=${conclusions_by_name[${req}]}"
                ;;
        esac
    done

    log "INFO" "considered=${considered} pending=${pending} failed=${failed} missing_required=${missing_required} ignored_cancelled=${ignored_cancelled}"

    if [[ "${failed}" -gt 0 ]]; then
        if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
            {
                echo "## PR checks gate (failed)"
                echo ""
                echo "| Workflow | Status | Conclusion |"
                echo "| :--- | :--- | :--- |"
                for line in "${summaries[@]}"; do
                    IFS='|' read -r n s c _ <<<"${line}"
                    echo "| ${n} | ${s} | ${c} |"
                done
            } >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
            echo "::error::One or more PR checks failed for ${COMMIT_SHA}"
        fi
        exit 1
    fi

    if [[ "${considered}" -gt 0 && "${pending}" -eq 0 && "${missing_required}" -eq 0 ]]; then
        log "INFO" "All ${considered} PR workflow run(s) succeeded or were skipped; required set present."
        if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
            {
                echo "## PR checks gate (passed)"
                echo ""
                echo "All ${considered} pull_request workflow run(s) for \`${COMMIT_SHA}\` concluded successfully"
                echo "(excluding \`${EXCLUDE_WORKFLOW_NAME}\`; required: \`${REQUIRED_WORKFLOWS}\`; ignored cancelled=${ignored_cancelled})."
            } >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
        fi
        exit 0
    fi

    log "INFO" "Still waiting; sleeping ${POLL_SECONDS}s"
    sleep "${POLL_SECONDS}"
done

log "ERROR" "Timed out after ${TIMEOUT_SECONDS}s waiting for checks on ${COMMIT_SHA}"
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::error::Timed out waiting for PR checks on ${COMMIT_SHA}"
fi
exit 1
