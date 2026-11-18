# CI Workflows & Scripts

All GitHub Actions workflows live under `.github/workflows/`. Dev/PR image tags and TestPyPI dev-tag publishing are disabled — container images are published only from `main` (or manual `workflow_dispatch` with `push=true`).

## Active Workflows

| Workflow | File | Triggers | What it runs |
| --- | --- | --- | --- |
| **Backend CI** | [`workflows/backend-ci.yml`](./workflows/backend-ci.yml) | PR + push to `main` (ignores `docs/**` & `modules/web/{src,e2e}/**`), weekly cron | `ruff check`, `ruff format --check`, `mypy backend/src`, `export_openapi.sh --check`, `migration_check.sh` (Postgres 15), `bin/bash/test.sh` |
| **Web CI** | [`workflows/web-ci.yml`](./workflows/web-ci.yml) | PR + push to `main` (`modules/web/**`, `docker/web/**`, `package.json`, `pnpm-lock.yaml`) | `pnpm web:check-types`, `pnpm web:lint`, `pnpm web:test:coverage`, `pnpm web:build`, plus `docker/web/Dockerfile` CSP header smoke |
| **Web E2E** | [`workflows/web-e2e.yml`](./workflows/web-e2e.yml) | PR (`modules/web/e2e/**`), weekly cron, `workflow_dispatch` | Compose stack + Playwright + axe + Lighthouse |
| **Security & Supply Chain** | [`workflows/security.yml`](./workflows/security.yml) | PR + push to `main`, weekly cron, `workflow_dispatch` | Gitleaks secret scan + `.github/scripts/supply_chain_check.sh` |
| **Publish Container Images** | [`workflows/publish-images.yml`](./workflows/publish-images.yml) | Push to `main` (`backend/**`, `modules/web/**`, `docker/**`), `workflow_dispatch` | Matrix (`api` + `web`) build → Trivy `CRITICAL`/`HIGH` scan → smoke script → GHCR push (`latest`, `sha-<commit>`; no `dev` tags) |

## Local Verification

```bash
# Backend
poetry run ruff check backend/src backend/tests
poetry run ruff format --check backend/src backend/tests
poetry run mypy backend/src
./bin/bash/export_openapi.sh --check
poetry run pytest

# Web
pnpm web:check-types
pnpm web:lint
pnpm web:test
pnpm web:build

# Supply chain
/bin/bash .github/scripts/supply_chain_check.sh
```
