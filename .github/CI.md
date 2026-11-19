# CI Workflows & Scripts

Single-purpose GitHub Actions workflows live under `.github/workflows/`, sharing the composite Poetry setup action in [`.github/actions/setup-poetry/action.yml`](./actions/setup-poetry/action.yml). Dev/PR release tags are disabled: `release.yml` runs tag-only `python-semantic-release` on `main` and dispatches `docker-release.yml` at the new `v*` tag.

## Active Workflows

| Workflow | File | Triggers | What it runs |
| --- | --- | --- | --- |
| **Code Quality Control** | [`workflows/quality-control.yml`](./workflows/quality-control.yml) | PR + push to `main` (ignores `docs/**`), weekly cron | `setup-poetry` + `pre-commit` (`ruff`, `ruff-format`, `mypy`, `sqlfluff`, `shellcheck`, `hadolint`, `yamllint`, `actionlint`, `markdownlint`) |
| **Unittests Python** | [`workflows/unittests-python.yml`](./workflows/unittests-python.yml) | PR + push to `main` (ignores `docs/**` & `modules/web/{src,e2e}/**`), weekly cron | `setup-poetry` + Postgres 15 → `./scripts/export_openapi.sh --check` → `.github/scripts/migration_check.sh` → `pytest --cov=modules/backend/src` → Codecov |
| **Frontend Quality** | [`workflows/frontend-quality.yml`](./workflows/frontend-quality.yml) | PR + push to `main` (`modules/web/**`, lockfiles) | `pnpm web:check-types`, `pnpm web:lint`, `pnpm web:test:coverage`, `pnpm web:build`, plus `modules/web/Dockerfile` build + `deploy/scripts/web_image_smoke.sh` |
| **Web E2E** | [`workflows/web-e2e.yml`](./workflows/web-e2e.yml) | PR (`modules/web/e2e/**`, `scripts/web_e2e_seed.*`), weekly cron, `workflow_dispatch` | `./deploy/scripts/deploy-dev.sh up --build api` + Playwright + axe + Lighthouse |
| **Semantic Release** | [`workflows/release.yml`](./workflows/release.yml) | Push to `main`, `workflow_dispatch` | Tag-only `python-semantic-release` on `main` (`v{version}`, major capped at minor); dispatches `docker-release.yml` at the new tag |
| **Publish container images** | [`workflows/docker-release.yml`](./workflows/docker-release.yml) | Push `v*` tags, `workflow_dispatch` (guarded to tag or `main`) | Matrix (`save-ma-money-backend` from `modules/backend`, `save-ma-money-web` from `modules/web/Dockerfile`) → Trivy `CRITICAL`/`HIGH` scan → smoke script → GHCR push |
| **Supply Chain Check** | [`workflows/supply-chain-check.yml`](./workflows/supply-chain-check.yml) | PR + push to `main` (dep/CI files), weekly cron | `setup-poetry` + `.github/scripts/supply_chain_check.sh` (`poetry check`, module version check, `pip-audit`) |
| **Secret Scan** | [`workflows/gitleaks.yml`](./workflows/gitleaks.yml) | PR + push to `main`, weekly cron | Gitleaks secret scan |
| **Trivy Security Scan** | [`workflows/trivy.yml`](./workflows/trivy.yml) | PR + push to `main`, weekly cron | Filesystem vuln + misconfig scan (`CRITICAL`/`HIGH`) → SARIF upload |
| **CodeQL Analysis** | [`workflows/codeql.yml`](./workflows/codeql.yml) | PR + push to `main`, weekly cron | CodeQL `security-extended` for `python` and `javascript-typescript` |
| **Bash Security** | [`workflows/bash-security.yml`](./workflows/bash-security.yml) | PR (`scripts/**`, `deploy/scripts/**`, `.github/scripts/**`) | ShellCheck security-relevant rules |
| **Branch Sync Check** | [`workflows/branch-sync.yml`](./workflows/branch-sync.yml) | PR (`opened`, `synchronize`, `reopened`) | `.github/scripts/branch_sync_check.sh` (fail when behind `origin/main`) |

## Local Verification

```bash
# Backend
poetry install --with development,pre-commit
pre-commit run --all-files
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
