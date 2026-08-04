#!/usr/bin/env bash
# Local pre-commit wrapper for modules/web (ESLint, Prettier, tsc, Vitest related).
# Skips in CI — web quality is gated by .github/workflows/web-ci.yml (and quality-control SKIP).
#
# Usage: pre_commit_web.sh <eslint|prettier|tsc|test> [repo-relative or abs paths...]
#
# Complements the usual husky+lint-staged JS stack by wiring the same tools through
# this repo's pre-commit SSOT (no husky). Scoped to modules/web only.

set -euo pipefail

if [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    exit 0
fi

usage() {
    echo "usage: pre_commit_web.sh <eslint|prettier|tsc|test> [files...]" >&2
    exit 2
}

if [[ $# -lt 1 ]]; then
    usage
fi

CMD="$1"
shift

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB="${ROOT}/modules/web"

if [[ ! -d "${WEB}" ]]; then
    echo "modules/web not found at ${WEB}" >&2
    exit 1
fi

if [[ ! -d "${WEB}/node_modules" ]]; then
    echo "modules/web/node_modules missing. From repo root run: pnpm install" >&2
    exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm not found on PATH (need pnpm 9+ / Node 22+). See modules/web/README.md" >&2
    exit 1
fi

cd "${WEB}"

# Map repo-root or absolute paths → paths relative to modules/web.
rel_files=()
for f in "$@"; do
    if [[ -z "${f}" ]]; then
        continue
    fi
    abs="${f}"
    if [[ "${abs}" != /* ]]; then
        abs="${ROOT}/${f}"
    fi
    # Normalize .. segments when possible
    if [[ -e "${abs}" ]]; then
        abs="$(cd "$(dirname "${abs}")" && pwd)/$(basename "${abs}")"
    fi
    case "${abs}" in
        "${WEB}"/*)
            rel="${abs#"${WEB}/"}"
            if [[ -f "${WEB}/${rel}" ]]; then
                rel_files+=("${rel}")
            fi
            ;;
        *)
            # Ignore files outside modules/web (hook file filter should prevent this).
            ;;
    esac
done

run_eslint() {
    if ((${#rel_files[@]} == 0)); then
        exit 0
    fi
    # Auto-fix + fail on remaining warnings (PDF recommendation).
    # --no-warn-ignored: staged generated files (e.g. src/types/api.d.ts) are
    # eslintignored; without this flag ESLint emits a warning that fails --max-warnings=0.
    pnpm exec eslint --fix --max-warnings=0 --no-warn-ignored -- "${rel_files[@]}"
}

run_prettier() {
    if ((${#rel_files[@]} == 0)); then
        exit 0
    fi
    pnpm exec prettier --write -- "${rel_files[@]}"
}

run_tsc() {
    # Project-wide check (tsc cannot reliably typecheck a partial file set with -b).
    pnpm exec tsc -b --pretty false
}

run_test() {
    if ((${#rel_files[@]} == 0)); then
        exit 0
    fi
    # Related tests only — avoid full suite on every commit (PDF pro tip).
    pnpm exec vitest related --run --passWithNoTests -- "${rel_files[@]}"
}

case "${CMD}" in
    eslint)
        run_eslint
        ;;
    prettier)
        run_prettier
        ;;
    tsc)
        run_tsc
        ;;
    test)
        run_test
        ;;
    *)
        usage
        ;;
esac
