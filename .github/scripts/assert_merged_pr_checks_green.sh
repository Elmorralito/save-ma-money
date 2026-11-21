#!/usr/bin/env bash
# Gate a main-tip release: the squash/merge commit must map to a merged PR
# whose head commit had every applicable check individually green.
#
# Required check jobs (when triggered by the PR's changed files / author):
#   - Branch Sync Check (job name: Not behind main; skipped for dependabot[bot])
#   - Code Quality Control (job: quality-control; skips docs + pure JS manifests)
#   - Unittests Python (job: unittests-python; backend/Poetry/OpenAPI paths)
#   - Frontend Quality (jobs: frontend, frontend-docker; web/lockfile paths)
#   - Checkov IaC Scan (job name: Checkov (Dockerfiles); Dockerfile/checkov paths)
#
# Env:
#   GITHUB_REPOSITORY  owner/name (required)
#   GITHUB_SHA         commit on main to gate (required)
#   GH_TOKEN           token with pull-requests:read + checks:read (required)
#
# Individual verdicts come from GraphQL statusCheckRollup contexts (needs
# checks:read). Do not call Checks REST check-runs — that 403s for
# GITHUB_TOKEN even with checks:write.
#
# Exit 0 only when all latest check runs/statuses are green (allowing NEUTRAL
# only on Trivy/CodeQL Code Scanning summaries, and expected SKIPPED checks on
# dependabot[bot] PRs) and every path-applicable required gate ran and passed.

set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
SHA="${GITHUB_SHA:?GITHUB_SHA is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"

OWNER="${REPO%%/*}"
NAME="${REPO#*/}"

if [[ -z "${OWNER}" || -z "${NAME}" || "${OWNER}" == "${NAME}" ]]; then
  echo "::error::GITHUB_REPOSITORY must be owner/name, got '${REPO}'"
  exit 1
fi

echo "Resolving merged PR for commit ${SHA}..."

PRS_JSON="$(
  gh api \
    -H "Accept: application/vnd.github+json" \
    "repos/${REPO}/commits/${SHA}/pulls" \
    --paginate
)"

PR_COUNT="$(jq 'length' <<<"${PRS_JSON}")"
if [[ "${PR_COUNT}" -eq 0 ]]; then
  echo "::error::No pull request associated with ${SHA}."
  echo "Direct pushes to main cannot publish a release tag; merge via a green PR."
  exit 1
fi

PR_JSON="$(
  jq -c --arg sha "${SHA}" '
    map(select(.merged_at != null and .merge_commit_sha == $sha))
    | if length > 0 then .[0]
      else map(select(.merged_at != null)) | .[0] // empty
      end
  ' <<<"${PRS_JSON}"
)"

if [[ -z "${PR_JSON}" || "${PR_JSON}" == "null" ]]; then
  echo "::error::Associated PR(s) for ${SHA} are not merged."
  jq -r '.[] | "- #\(.number) state=\(.state) merge_commit_sha=\(.merge_commit_sha // "null")"' <<<"${PRS_JSON}"
  exit 1
fi

PR_NUMBER="$(jq -r '.number' <<<"${PR_JSON}")"
MERGE_SHA="$(jq -r '.merge_commit_sha // empty' <<<"${PR_JSON}")"
PR_URL="$(jq -r '.html_url' <<<"${PR_JSON}")"
HEAD_SHA="$(jq -r '.head.sha' <<<"${PR_JSON}")"
PR_AUTHOR="$(jq -r '.user.login // ""' <<<"${PR_JSON}")"

echo "PR #${PR_NUMBER} (${PR_URL}) author=${PR_AUTHOR}"
echo "merge_commit_sha=${MERGE_SHA:-none}"
echo "head_sha=${HEAD_SHA}"

if [[ -n "${MERGE_SHA}" && "${MERGE_SHA}" != "${SHA}" ]]; then
  echo "::warning::Tip ${SHA} is not the PR merge commit (${MERGE_SHA}); still checking PR head checks."
fi

PR_FILES="$(
  gh api \
    -H "Accept: application/vnd.github+json" \
    "repos/${REPO}/pulls/${PR_NUMBER}/files" \
    --paginate \
    --jq '.[].filename'
)"

IS_DEPENDABOT=0
if [[ "${PR_AUTHOR}" == "dependabot[bot]" ]]; then
  IS_DEPENDABOT=1
fi

IS_DOCS_ONLY=0
if [[ -n "${PR_FILES}" ]]; then
  IS_DOCS_ONLY=1
  while IFS= read -r file; do
    [[ -z "${file}" ]] && continue
    if [[ "${file}" != docs/* ]]; then
      IS_DOCS_ONLY=0
      break
    fi
  done <<<"${PR_FILES}"
fi

echo "is_dependabot=${IS_DEPENDABOT} is_docs_only=${IS_DOCS_ONLY}"

# --- Rollup + per-check contexts (GraphQL; works with GITHUB_TOKEN) ----------
ROLLUP_JSON="$(
  # GraphQL query is a literal; shellcheck SC2016 is expected.
  # shellcheck disable=SC2016
  gh api graphql \
    -f owner="${OWNER}" \
    -f name="${NAME}" \
    -f sha="${HEAD_SHA}" \
    -f query='
      query($owner: String!, $name: String!, $sha: GitObjectID!) {
        repository(owner: $owner, name: $name) {
          object(oid: $sha) {
            ... on Commit {
              statusCheckRollup {
                state
                contexts(first: 100) {
                  nodes {
                    ... on StatusContext {
                      context
                      state
                      createdAt
                    }
                    ... on CheckRun {
                      name
                      conclusion
                      status
                      completedAt
                      startedAt
                    }
                  }
                }
              }
            }
          }
        }
      }
    '
)"

STATE="$(jq -r '.data.repository.object.statusCheckRollup.state // empty' <<<"${ROLLUP_JSON}")"
if [[ -z "${STATE}" ]]; then
  echo "::error::No statusCheckRollup on PR head ${HEAD_SHA}."
  echo "Refusing to publish a release tag without a green PR check rollup."
  jq . <<<"${ROLLUP_JSON}" >&2 || true
  exit 1
fi
echo "PR head statusCheckRollup.state=${STATE}"
if [[ "${STATE}" == "PENDING" || "${STATE}" == "EXPECTED" ]]; then
  echo "::error::Merged PR #${PR_NUMBER} head rollup is ${STATE}."
  echo "Refusing to publish the release tag while checks are incomplete."
  exit 1
fi
if [[ "${STATE}" != "SUCCESS" ]]; then
  echo "::warning::PR head statusCheckRollup.state is ${STATE}; verifying latest deduplicated check verdicts."
fi

# Deduplicate by name/context keeping the latest run (handles superseded CANCELLED runs).
CHECKS_JSON="$(
  jq '
    [
      .data.repository.object.statusCheckRollup.contexts.nodes[]?
      | select(.name != null)
      | {
          name: .name,
          status: ((.status // "COMPLETED") | ascii_downcase),
          conclusion: ((.conclusion // "") | ascii_downcase),
          sort_ts: (.completedAt // .startedAt // "")
        }
    ]
    | sort_by(.name, .sort_ts)
    | group_by(.name)
    | map(.[-1])
    | {check_runs: .}
  ' <<<"${ROLLUP_JSON}"
)"

STATUSES_JSON="$(
  jq '
    {
      statuses: (
        [
          .data.repository.object.statusCheckRollup.contexts.nodes[]?
          | select(.context != null)
          | {
              context: .context,
              state: ((.state // "") | ascii_downcase),
              sort_ts: (.createdAt // "")
            }
        ]
        | sort_by(.context, .sort_ts)
        | group_by(.context)
        | map(.[-1])
      )
    }
  ' <<<"${ROLLUP_JSON}"
)"

echo "Individual checks (latest per name):"
jq -r '
  .check_runs
  | sort_by(.name)
  | .[]
  | "- \(.name): status=\(.status) conclusion=\(.conclusion // "null")"
' <<<"${CHECKS_JSON}"

echo "Commit statuses (latest per context):"
jq -r '
  (.statuses // [])
  | if length == 0 then "- (none)"
    else
      sort_by(.context)
      | .[]
      | "- \(.context): state=\(.state)"
    end
' <<<"${STATUSES_JSON}"

FAILED_INDIVIDUAL="$(
  # Literal ${{ matrix.language }} appears when CodeQL matrix skips pre-expansion.
  # shellcheck disable=SC2016
  jq -r --argjson is_bot "${IS_DEPENDABOT}" '
    [
      .check_runs[]
      | select(
          (.status != "completed")
          or (
            ((.conclusion // "") != "success")
            and ((.conclusion == "neutral" and (.name == "Trivy" or .name == "CodeQL")) | not)
            and ((
              $is_bot == 1
              and .conclusion == "skipped"
              and (.name == "Analyze (python)"
                or .name == "Analyze (javascript-typescript)"
                or .name == "Analyze (${{ matrix.language }})"
                or .name == "gitleaks"
                or .name == "Not behind main"
                or .name == "branch-sync"
                or .name == "playwright")
            ) | not)
          )
        )
      | "\(.name) [status=\(.status) conclusion=\(.conclusion // "null")]"
    ] | .[]
  ' <<<"${CHECKS_JSON}"
)"

FAILED_STATUSES="$(
  jq -r '
    [
      (.statuses // [])[]
      | select((.state // "") != "success")
      | "\(.context) [state=\(.state)]"
    ] | .[]
  ' <<<"${STATUSES_JSON}"
)"

GATE_FAIL=0

if [[ -n "${FAILED_INDIVIDUAL}" ]]; then
  echo "::error::One or more check runs were not individually green:"
  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    echo "  - ${line}"
  done <<<"${FAILED_INDIVIDUAL}"
  GATE_FAIL=1
fi

if [[ -n "${FAILED_STATUSES}" ]]; then
  echo "::error::One or more commit statuses were not individually green:"
  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    echo "  - ${line}"
  done <<<"${FAILED_STATUSES}"
  GATE_FAIL=1
fi

# --- Path-aware required gate checks -----------------------------------------
NEED_QC=0
NEED_UNITTESTS=0
NEED_FRONTEND=0
NEED_CHECKOV=0

if [[ "${IS_DOCS_ONLY}" -eq 0 ]]; then
  while IFS= read -r file; do
    [[ -z "${file}" ]] && continue

    # quality-control.yml ignores docs/** and pure JS manifests/lockfiles.
    case "${file}" in
      docs/*|package.json|pnpm-lock.yaml|pnpm-workspace.yaml|.nvmrc|modules/web/package.json)
        ;;
      *)
        NEED_QC=1
        ;;
    esac

    # unittests-python.yml paths (excludes modules/backend/Dockerfile).
    case "${file}" in
      modules/backend/Dockerfile)
        ;;
      pyproject.toml|poetry.toml|modules/backend/*|modules/web/openapi/*|scripts/export_openapi.*|scripts/utils.sh|.github/scripts/migration_check.sh|.github/actions/setup-poetry/*|.github/workflows/unittests-python.yml)
        NEED_UNITTESTS=1
        ;;
    esac

    # frontend-quality.yml paths.
    case "${file}" in
      modules/web/*|package.json|pnpm-lock.yaml|pnpm-workspace.yaml|.nvmrc|.node-version|.dockerignore|.github/workflows/frontend-quality.yml)
        NEED_FRONTEND=1
        ;;
    esac

    # checkov.yml paths.
    case "${file}" in
      Dockerfile|*/Dockerfile|.checkov.yaml|.pre-commit-config.yaml|.github/workflows/checkov.yml)
        NEED_CHECKOV=1
        ;;
    esac
  done <<<"${PR_FILES}"
fi

REQUIRED_PATTERNS=()
if [[ "${IS_DEPENDABOT}" -eq 0 ]]; then
  REQUIRED_PATTERNS+=('^(Not behind main|branch-sync|Branch Sync Check(/branch-sync)?)$')
fi
if [[ "${NEED_QC}" -eq 1 ]]; then
  REQUIRED_PATTERNS+=('^(quality-control|Code Quality Control(/quality-control)?)$')
fi
if [[ "${NEED_UNITTESTS}" -eq 1 ]]; then
  REQUIRED_PATTERNS+=('^(unittests-python|Unittests Python(/unittests-python)?)$')
fi
if [[ "${NEED_FRONTEND}" -eq 1 ]]; then
  REQUIRED_PATTERNS+=('^(frontend|Frontend Quality(/frontend)?)$')
  REQUIRED_PATTERNS+=('^(frontend-docker|Frontend Quality(/frontend-docker)?)$')
fi
if [[ "${NEED_CHECKOV}" -eq 1 ]]; then
  REQUIRED_PATTERNS+=('^(checkov|Checkov \(Dockerfiles\)|Checkov IaC Scan(/checkov)?)$')
fi

MISSING_REQUIRED=()
for pattern in "${REQUIRED_PATTERNS[@]}"; do
  MATCHED="$(
    jq -r --arg re "${pattern}" '
      [
        .check_runs[]
        | select(.name | test($re; "i"))
        | .name
      ] | unique | .[]
    ' <<<"${CHECKS_JSON}"
  )"
  if [[ -z "${MATCHED}" ]]; then
    MISSING_REQUIRED+=("${pattern}")
    continue
  fi
  BAD_REQUIRED="$(
    jq -r --arg re "${pattern}" '
      [
        .check_runs[]
        | select(.name | test($re; "i"))
        | select(
            (.status != "completed")
            or ((.conclusion // "") != "success")
          )
        | "\(.name) [status=\(.status) conclusion=\(.conclusion // "null")]"
      ] | .[]
    ' <<<"${CHECKS_JSON}"
  )"
  if [[ -n "${BAD_REQUIRED}" ]]; then
    echo "::error::Required gate check is not green:"
    while IFS= read -r line; do
      [[ -z "${line}" ]] && continue
      echo "  - ${line}"
    done <<<"${BAD_REQUIRED}"
    GATE_FAIL=1
  else
    echo "Required OK: ${MATCHED}"
  fi
done

if [[ "${#MISSING_REQUIRED[@]}" -gt 0 ]]; then
  echo "::error::Required gate check(s) missing on PR head ${HEAD_SHA}:"
  for pattern in "${MISSING_REQUIRED[@]}"; do
    echo "  - pattern ${pattern}"
  done
  echo "All path-applicable gates must run and succeed before publishing a release tag."
  GATE_FAIL=1
fi

CHECK_COUNT="$(jq '.check_runs | length' <<<"${CHECKS_JSON}")"
if [[ "${CHECK_COUNT}" -eq 0 ]]; then
  echo "::error::No check runs found on PR head ${HEAD_SHA}."
  GATE_FAIL=1
fi

if [[ "${GATE_FAIL}" -ne 0 ]]; then
  echo "Refusing to publish the release tag."
  exit 1
fi

echo "Merged PR #${PR_NUMBER}: all ${CHECK_COUNT} check run(s) and required gate(s) passed; release gate passed."
exit 0
