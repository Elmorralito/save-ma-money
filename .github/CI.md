# CI Workflows & Scripts

Single-purpose GitHub Actions workflows live under `.github/workflows/`, sharing the composite Poetry setup action in [`.github/actions/setup-poetry/action.yml`](./actions/setup-poetry/action.yml). Dev/PR release tags are disabled: `release.yml` runs tag-only `python-semantic-release` on `main` and dispatches `docker-release.yml` at the new `v*` tag.

## Active Workflows

| Workflow | File | Triggers | What it runs |
| --- | --- | --- | --- |
| **Code Quality Control** | [`workflows/quality-control.yml`](./workflows/quality-control.yml) | PR (ignores `docs/**` & JS manifests/lockfiles), weekly cron | `setup-poetry` + `pre-commit` (`ruff`, `ruff-format`, `mypy`, `sqlfluff`, `shellcheck`, `hadolint`, `yamllint`, `actionlint`, `markdownlint`) |
| **Unittests Python** | [`workflows/unittests-python.yml`](./workflows/unittests-python.yml) | PR (`modules/backend/**` excl. `Dockerfile`, `pyproject.toml`, `poetry.toml`, OpenAPI/migrations), weekly cron | `setup-poetry` + Postgres 15 → `./scripts/export_openapi.sh --check` → `.github/scripts/migration_check.sh` → `pytest --cov=modules/backend/src` → Codecov |
| **Frontend Quality** | [`workflows/frontend-quality.yml`](./workflows/frontend-quality.yml) | PR (`modules/web/**`, lockfiles) | `pnpm web:check-types`, `pnpm web:lint`, `pnpm web:test:coverage`, `pnpm web:build`, plus `modules/web/Dockerfile` build + `deploy/scripts/web_image_smoke.sh` |
| **Web E2E** | [`workflows/web-e2e.yml`](./workflows/web-e2e.yml) | PR (`modules/web/e2e/**`, `scripts/web_e2e_seed.*`, skips `dependabot[bot]` & `skip-web-e2e`), weekly cron, `workflow_dispatch` | `./deploy/scripts/deploy-dev.sh up --build api` + Playwright + axe + Lighthouse |
| **Checkov IaC Scan** | [`workflows/checkov.yml`](./workflows/checkov.yml) | PR + push to `main` (`**/Dockerfile`, `.checkov.yaml`, `.pre-commit-config.yaml`, skips `skip-scan-image`) | `checkov` pre-commit manual stage (Dockerfile security & best-practice scan) |
| **Semantic Release** | [`workflows/release.yml`](./workflows/release.yml) | Push to `main`, `workflow_dispatch` | Merged-PR GraphQL gate ([`assert_merged_pr_checks_green.sh`](./scripts/assert_merged_pr_checks_green.sh)) → tag-only `python-semantic-release` (`v{version}`, capped at minor) → dispatches `docker-release.yml` |
| **Publish container images** | [`workflows/docker-release.yml`](./workflows/docker-release.yml) | Push `v*` tags, `workflow_dispatch` (guarded to tag or `main`) | Matrix (`save-ma-money-backend` from `modules/backend`, `save-ma-money-web` from `modules/web/Dockerfile`) → Trivy `CRITICAL`/`HIGH` scan → smoke script → GHCR push |
| **Supply Chain Check** | [`workflows/supply-chain-check.yml`](./workflows/supply-chain-check.yml) | PR + push to `main` (`pyproject.toml`, `modules/backend/pyproject.toml`, `poetry.toml`, supply-chain CI/scripts), weekly cron | `setup-poetry` + `.github/scripts/supply_chain_check.sh` (`poetry check`, module version check, `pip-audit`) |
| **Secret Scan** | [`workflows/gitleaks.yml`](./workflows/gitleaks.yml) | PR (skips `dependabot[bot]`), weekly cron | Gitleaks secret scan |
| **Trivy Security Scan** | [`workflows/trivy.yml`](./workflows/trivy.yml) | PR, weekly cron | Filesystem vuln + misconfig scan (`CRITICAL`/`HIGH`) → SARIF upload |
| **CodeQL Analysis** | [`workflows/codeql.yml`](./workflows/codeql.yml) | PR (skips `dependabot[bot]`), weekly cron | CodeQL `security-extended` for `python` and `javascript-typescript` |
| **Bash Security** | [`workflows/bash-security.yml`](./workflows/bash-security.yml) | PR (`scripts/**`, `deploy/scripts/**`, `.github/scripts/**`, `.github/semgrep/**`) | ShellCheck security-relevant rules + Semgrep (`bash-security.yml` + `p/trailofbits`) |
| **Branch Sync Check** | [`workflows/branch-sync.yml`](./workflows/branch-sync.yml) | PR (`opened`, `synchronize`, `reopened`, `ready_for_review`, skips `dependabot[bot]`) | `.github/scripts/branch_sync_check.sh` (fail when behind `origin/main`) |

## Main Release Gate

`Code Quality Control`, `Unittests Python`, `Frontend Quality`, `CodeQL Analysis`, `Secret Scan`, and `Trivy Security Scan` run on PRs (and weekly schedules where configured) rather than re-running on every `push` to `main`. Before tagging a release on `main`, [`workflows/release.yml`](./workflows/release.yml) runs [`.github/scripts/assert_merged_pr_checks_green.sh`](./scripts/assert_merged_pr_checks_green.sh):

1. Resolves the squash/merge commit's associated merged PR (direct pushes to `main` cannot release).
2. Queries GraphQL `statusCheckRollup` (`checks: read`; REST `check-runs` returns 403 for `GITHUB_TOKEN`) and deduplicates by check/context name keeping the latest run.
3. Requires every latest check run and commit status to be green (`Trivy` and `CodeQL` Code Scanning summaries may be `NEUTRAL`; `dependabot[bot]` PRs allow expected skipped jobs for CodeQL/Gitleaks/Branch Sync/Web E2E).
4. Enforces path-applicable required gates based on the PR's changed files (`Not behind main` for non-Dependabot PRs, `quality-control`, `unittests-python`, `frontend` + `frontend-docker`, and `Checkov (Dockerfiles)`). Applying `skip-quality` or `skip-scan-image` blocks release tagging.

## Local Verification

```bash
# Backend
poetry install --with development,pre-commit
pre-commit run --all-files
pre-commit run checkov --hook-stage manual --all-files    # needs Docker
./scripts/export_openapi.sh --check
poetry run pytest

# Web
pnpm install --frozen-lockfile
pnpm web:check-types
pnpm web:lint
pnpm web:test
pnpm web:build

# Local Compose stack
./deploy/scripts/deploy-dev.sh up --build
./deploy/scripts/deploy-dev.sh down
```
