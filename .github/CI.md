# Continuous integration

GitHub Actions workflows, validation scripts, and local pre-commit hooks for **save-ma-money**.

| Constant                  | Value                                                          |
| :------------------------ | :------------------------------------------------------------- |
| Python                    | 3.12                                                           |
| Poetry                    | 2.1.3                                                          |
| PostgreSQL (migration CI) | 15-alpine                                                      |
| Lock file                 | `poetry.lock` is **gitignored** — CI resolves deps at run time |

**Related docs:** [`.agents/AGENTS.md`](../.agents/AGENTS.md) · [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) · [`.strata/MANIFEST.md`](../.strata/MANIFEST.md) · [Issue #41](https://github.com/Elmorralito/save-ma-money/issues/41) (security CI requirement)

---

## Contents

- [CI at a glance](#ci-at-a-glance)
- [Which checks run on my PR?](#which-checks-run-on-my-pr)
- [PR skip labels](#pr-skip-labels)
- [Workflow overview](#workflow-overview)
- [Run checks locally](#run-checks-locally)
- [Workflows in detail](#workflows-in-detail) (includes [Publish model package](#publish-model-package-ppt-024) + [dev TestPyPI](#publish-model-dev--testpypi))
- [CI Adoption Badge](#ci-adoption-badge)
- [Pre-commit hooks](#pre-commit-hooks)
- [Strata validation](#strata-validation)
- [Supporting scripts](#supporting-scripts)
- [PR checklist](#pr-checklist)
- [Troubleshooting](#troubleshooting)
- [Scheduled scans](#scheduled-scans)
- [Security tab integration](#security-tab-integration)
- [Environment variables](#environment-variables)
- [Toolchain pins](#toolchain-pins)

---

## CI at a glance

```mermaid
flowchart TB
    subgraph pr [Pull request]
        QC[Code Quality Control]
        WEB[Web CI]
        OAPI[OpenAPI Web Contract]
        GL[Secret Scan]
        SC[Supply Chain Check]
        MC[Migration Check]
        CQ[CodeQL Python]
        CQJS[CodeQL JS/TS]
        TR[Trivy Security Scan]
        BS[Bash Security]
        ST[Strata Check]
        SYN[Branch sync with main]
        DEV[Publish model dev TestPyPI]
    end

    subgraph main [Merge to main]
        AU[Auto Updates]
        REL[Release model PSR]
        PYPI[Publish model PyPI]
    end

    QC --> |pre-commit + pytest + Codecov| Pass1[Gate]
    WEB --> |pnpm lint/test/build + check-types + web image| PassWeb[Gate]
    OAPI --> |artifact vs app.openapi| PassOapi[Gate]
    GL --> |full history| Pass2[Gate]
    SC --> |poetry check + pip-audit| Pass3[Gate]
    MC --> |Alembic round-trip| Pass4[Gate]
    CQ --> |Python SAST| Pass5[Gate]
    CQJS --> |JS/TS SAST| Pass5b[Gate]
    TR --> |CVE + misconfig SARIF| Pass6[Gate]
    BS --> |ShellCheck security + Semgrep| Pass7[Gate]
    ST --> |.strata/ layout + pairing| Pass8[Gate]
    SYN --> |not behind origin/main| Pass9[Gate]

    Pass1 & PassWeb & PassOapi & Pass2 & Pass3 & Pass4 & Pass5 & Pass6 & Pass7 & Pass8 & Pass9 --> Merge[Merge]
    Pass1 & Pass2 & Pass9 --> |modules/model paths only| DEV
    Merge --> AU
    Merge --> |modules/model paths + releasable commits| REL
    REL --> |workflow_call on released=true| PYPI
    AU --> |CHANGELOG + badges| Push[Push to main]
```

> Path-filtered: Web CI and OpenAPI Web Contract only run when their path filters match; they are merge gates when present on the PR.

**Concurrency:** Most workflows use per-ref concurrency groups and **cancel in-progress** runs when a newer commit lands on the same branch.

**Local vs CI split:** Strata and MCP hooks run on `git commit` locally. GitHub Actions skips them in pre-commit (`SKIP=strata-validate,mcp-config-validate`) and uses dedicated workflows/scripts instead.

---

## Which checks run on my PR?

Use this matrix to predict required checks before opening a PR.

| Change type                                 | Quality Control | Web CI | OpenAPI contract | Gitleaks | Supply Chain | Migration | CodeQL Py | CodeQL JS | Trivy | Bash Sec | Strata | Branch sync |
| :------------------------------------------ | :-------------: | :----: | :--------------: | :------: | :----------: | :-------: | :-------: | :-------: | :---: | :------: | :----: | :---------: |
| `docs/**` only                              |        —        |   —    |        —         |    ✓     |      —       |     —     |     —     |     —     |   —   |    —     |   —    |      ✓      |
| `modules/web/**` only                       |        —        |   ✓    |       —\*        |    ✓     |      —       |     —     |     —     |    ✓†     |   —   |    —     |   ✓    |      ✓      |
| `modules/api/src/**` or model OpenAPI bleed |        ✓        |   —    |        ✓         |    ✓     |     —\*      |    —\*    |    ✓†     |     —     |  —\*  |    —     |   ✓    |      ✓      |
| `modules/model/**` or `modules/api/**`      |        ✓        |  —\*   |       —\*        |    ✓     |     —\*      |    —\*    |    ✓†     |     —     |  —\*  |    —     |   ✓    |      ✓      |
| `pyproject.toml` / module deps              |        ✓        |  —\*   |        —         |    ✓     |      ✓       |     —     |    ✓†     |     —     |   ✓   |    —     |   ✓‡   |      ✓      |
| Model / Alembic / `docker/database/**`      |        ✓        |   —    |        —         |    ✓     |     —\*      |     ✓     |    ✓†     |     —     |  —\*  |    —     |   ✓    |      ✓      |
| `bin/**` or `.github/scripts/**`            |        ✓        |   —    |       —\*        |    ✓     |     —\*      |    —\*    |     —     |     —     |   —   |    ✓     |  —\*   |      ✓      |
| `.strata/**` only (no `modules/` or `bin/`) |        ✓        |   —    |        —         |    ✓     |      —       |     —     |     —     |     —     |   —   |    —     |   —§   |      ✓      |
| `.github/workflows/**`                      |        ✓        |  —\*   |       —\*        |    ✓     |      ✓       |    —\*    |    —\*    |    —\*    |  —\*  |   —\*    |  —\*   |      ✓      |
| `.cursor/mcp.json`                          |        ✓        |   —    |        —         |    ✓     |      —       |     —     |     —     |     —     |   —   |    —     |   —    |      ✓      |

\* Runs only when matching [path filters](#workflow-overview) apply.
† CodeQL workflows run on PRs **targeting `main`** only (Python and JS/TS are separate workflows).
‡ Strata Check runs when root `pyproject.toml` changes (listed in its path filter).
§ Strata Check path filters do **not** include `.strata/**` — layout validation for memory-only edits is enforced locally via pre-commit, not this workflow.

**Always on PRs:** Secret Scan (Gitleaks) — no path filter, full history · Branch sync with main — fail if the PR head is behind `origin/main`.

**Model TestPyPI (optional publish, not a merge gate):** PRs that touch `modules/model/**` also run [Publish model (dev)](#publish-model-dev--testpypi) after the other PR checks pass. It is path-filtered and must not be required for merge (it waits on the other checks). Opt out with [`skip-dev-release`](#pr-skip-labels).

---

## PR skip labels

Durable **functional** labels (not `PPT-*`). Apply on a **PR** to skip the matching workflow job. Adding/removing the label re-triggers the workflow (`labeled` / `unlabeled`). **Push to `main`, schedules, and `workflow_dispatch` ignore these labels.**

| Label              | Skips workflow                       | File                                                         |
| ------------------ | ------------------------------------ | ------------------------------------------------------------ |
| `skip-dev-release` | Publish model (dev) TestPyPI preview | [`publish-model-dev.yml`](./workflows/publish-model-dev.yml) |
| `skip-strata`      | Strata Check                         | [`strata-check.yml`](./workflows/strata-check.yml)           |
| `skip-web-ci`      | Web CI (lint / Vitest / build)       | [`web-ci.yml`](./workflows/web-ci.yml)                       |
| `skip-web-e2e`     | Web E2E (Playwright / axe / LHCI)    | [`web-e2e.yml`](./workflows/web-e2e.yml)                     |
| `skip-quality`     | Code Quality Control (Python gate)   | [`quality-control.yml`](./workflows/quality-control.yml)     |
| `skip-migrations`  | Migration Check                      | [`migration-check.yml`](./workflows/migration-check.yml)     |
| `skip-openapi`     | OpenAPI Web Contract                 | [`openapi-contract.yml`](./workflows/openapi-contract.yml)   |

**Not skippable via label (by design):** Gitleaks, CodeQL, Trivy, Bash Security, Supply Chain, Branch sync — keep security and merge-hygiene gates honest.

**Use sparingly.** Prefer path filters and focused PRs. `skip-quality` / `skip-migrations` / `skip-openapi` are for rare noise (e.g. docs-only false positives), not for shipping untested code. Skipped jobs still appear as **Skipped** in the checks list; if a check is **required** in branch protection, confirm skipped-as-success is acceptable for that repo setting.

```bash
# Example: skip TestPyPI preview on a model docs PR
gh pr edit 123 --add-label skip-dev-release
```

---

## Workflow overview

| Workflow             | File                                                                     | Triggers                                                                     | Purpose                                                                                                                                           |
| :------------------- | :----------------------------------------------------------------------- | :--------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| Code Quality Control | [`workflows/quality-control.yml`](./workflows/quality-control.yml)       | PR + push to `main`; Mon 07:00 UTC; skips `docs/**` + web                    | pre-commit, pytest, Postgres live tests (B0), Codecov                                                                                             |
| Web CI               | [`workflows/web-ci.yml`](./workflows/web-ci.yml)                         | PR + push to `main` (`modules/web/**`, `docker/web/**`, pnpm lock/workspace) | pnpm lint / Vitest+coverage / audit (soft) / build + OpenAPI `check-types` + nginx image (tar export→load) + SPA header smoke (PPT-057 / PPT-063) |
| Web E2E              | [`workflows/web-e2e.yml`](./workflows/web-e2e.yml)                       | Nightly Mon 07:30 UTC; `workflow_dispatch`; PRs touching e2e/seed            | Compose API (`AUTH_PROVIDER=local`) + Playwright/axe + Lighthouse lab (PPT-056 / #121)                                                            |
| OpenAPI Web Contract | [`workflows/openapi-contract.yml`](./workflows/openapi-contract.yml)     | PR + push (API src, model model/access, web OpenAPI artifact)                | Offline OpenAPI dump vs committed `modules/web/openapi/openapi.json` (PPT-065)                                                                    |
| Migration Check      | [`workflows/migration-check.yml`](./workflows/migration-check.yml)       | PR + push to `main` (model/migration/integration paths)                      | PostgreSQL Alembic round-trip + drift check                                                                                                       |
| Supply Chain Check   | [`workflows/supply-chain-check.yml`](./workflows/supply-chain-check.yml) | PR + push (deps/workflow paths); Mon 08:00 UTC                               | `poetry check`, version metadata, `pip-audit`                                                                                                     |
| Secret Scan          | [`workflows/gitleaks.yml`](./workflows/gitleaks.yml)                     | **All PRs**; push to `main`; Mon 05:00 UTC                                   | Full-history secret detection                                                                                                                     |
| CodeQL Python        | [`workflows/codeql.yml`](./workflows/codeql.yml)                         | PR → `main` + push (`modules/{model,api}/**`); Mon 06:00 UTC                 | Python SAST (`security-extended`) — independent of JS/TS                                                                                          |
| CodeQL JS/TS         | [`workflows/codeql-javascript.yml`](./workflows/codeql-javascript.yml)   | PR → `main` + push (`modules/web/**`, pnpm); Mon 06:30 UTC                   | JavaScript/TypeScript SAST — runs when web/JS/TS paths change; independent of Python                                                              |
| Trivy Security Scan  | [`workflows/trivy.yml`](./workflows/trivy.yml)                           | PR + push (manifest/docker paths); Mon 07:00 UTC                             | Filesystem CVE + IaC misconfig (SARIF)                                                                                                            |
| Bash Security        | [`workflows/bash-security.yml`](./workflows/bash-security.yml)           | **PR only** (shell/script paths)                                             | ShellCheck security codes + Semgrep bash rules                                                                                                    |
| Strata Check         | [`workflows/strata-check.yml`](./workflows/strata-check.yml)             | PR + push to `main` (code/bin paths)                                         | `.strata/` layout + strict code/memory pairing                                                                                                    |
| Branch sync          | [`workflows/branch-sync.yml`](./workflows/branch-sync.yml)               | **All PRs**; `workflow_dispatch`                                             | Fail if branch is behind `origin/main` (needs merge/rebase)                                                                                       |
| Auto Updates         | [`workflows/auto-updates.yml`](./workflows/auto-updates.yml)             | Push or merged PR to `main`                                                  | Regenerate [`CHANGELOG.md`](../CHANGELOG.md) and badges                                                                                           |
| CI Adoption Badge    | [`workflows/ci-badge.yml`](./workflows/ci-badge.yml)                     | PR + push to `main`; Mon 06:00 UTC; `workflow_dispatch`                      | Score CI maturity and update README adoption badge                                                                                                |
| Release model (PSR)  | [`workflows/release-model.yml`](./workflows/release-model.yml)           | Push `main` (model paths); `workflow_dispatch`                               | python-semantic-release → `model-v*` + `modules/model/CHANGELOG.md`; calls publish on release                                                     |
| Publish model (PyPI) | [`workflows/publish-model.yml`](./workflows/publish-model.yml)           | `workflow_call`; tag `model-v*`; `workflow_dispatch`                         | Build + OIDC publish `papita-transactions-model` (PPT-024)                                                                                        |
| Publish model (dev)  | [`workflows/publish-model-dev.yml`](./workflows/publish-model-dev.yml)   | PR (model paths) after other checks pass                                     | Stamp `{version}.dev{run_id}` → TestPyPI (same-repo, non-draft)                                                                                   |

---

## Run checks locally

Mirror CI before pushing:

```bash
# One-shot quality gate (same hooks as CI, plus local Strata/MCP when paths match)
pre-commit run --all-files

# Tests + coverage report → docs/coverage.xml (same entry point as CI)
/bin/bash ./bin/test.sh

# Supply chain (deps or workflow script changes)
/bin/bash .github/scripts/supply_chain_check.sh

# Branch not behind main (same gate as branch-sync.yml)
git fetch origin main
/bin/bash .github/scripts/branch_sync_check.sh

# Strata layout + strict pairing (PR range vs main)
STRATA_STRICT_MODULES=1 STRATA_BASE_REF=origin/main /bin/bash .github/scripts/strata_check.sh

# Strata against staged files only (what pre-commit runs)
/bin/bash .github/scripts/pre_commit_strata.sh

# MCP config (when .cursor/mcp.json exists)
/bin/bash .github/scripts/mcp_config_check.sh

# Migrations — full CI sequence (requires running Postgres)
export DB_URL="postgresql+psycopg2://papita:papita@localhost:5432/papita_test"
/bin/bash .github/scripts/migration_check.sh

# Web OpenAPI contract (PPT-065 strategy B — offline; no Compose)
make check-openapi
pnpm install --frozen-lockfile && make check-types
# After API schema changes: make web-openapi && commit artifact + api.d.ts

# Bash security gate (ShellCheck security codes + Semgrep; Docker required for Semgrep)
SECURITY_CODES='SC2046,SC2048,SC2068,SC2086,SC2115,SC2145,SC2154,SC2164,SC2206,SC2207,SC2294,SC2479'
shellcheck -S warning -i "$SECURITY_CODES" bin/*.sh .github/scripts/*.sh
docker run --rm -v "$PWD:/src" -w /src \
  semgrep/semgrep:1.128.1@sha256:fca58525689355641019c05ab49dcc5bc3a1eb7e044f35014ee39594b5aa4fc1 \
  semgrep scan --config=.github/semgrep/bash-security.yml --config=p/trailofbits \
  --error --metrics=off --include='*.sh' bin/ .github/scripts/
```

Install tooling once:

```bash
poetry install --no-interaction
pre-commit install   # optional but recommended for commit-time hooks
```

---

## Workflows in detail

### Branch sync with main

|               |                                                                                     |
| :------------ | :---------------------------------------------------------------------------------- |
| **Trigger**   | All pull requests; optional `workflow_dispatch`                                     |
| **Script**    | [`scripts/branch_sync_check.sh`](./scripts/branch_sync_check.sh)                    |
| **Pass when** | PR head is **not behind** `origin/main` (ahead-only feature commits are fine)       |
| **Fail when** | `git rev-list --count HEAD..origin/main` &gt; 0 — merge or rebase `main`, then push |

Checks out the PR head SHA (not the temporary merge commit) so the behind-count matches what you see locally.

### Release model (python-semantic-release, PPT-024)

|                 |                                                                                                                |
| :-------------- | :------------------------------------------------------------------------------------------------------------- |
| **Trigger**     | Push to `main` touching `modules/model/**`; optional `workflow_dispatch` (+ force bump)                        |
| **Tool**        | [python-semantic-release](https://python-semantic-release.readthedocs.io/) v10 (`directory: modules/model`)    |
| **Outputs**     | Bumps `modules/model/pyproject.toml`, updates **`modules/model/CHANGELOG.md`**, tags `model-v*`                |
| **Publish**     | On `released=true`, **`workflow_call`** → [`publish-model.yml`](./workflows/publish-model.yml) (`target=pypi`) |
| **Not touched** | Repo-root [`CHANGELOG.md`](../CHANGELOG.md) — owned by [Auto Updates](#auto-updates) only                      |

**Commit style for bumps:** Conventional Commits with model scope, e.g. `feat(model): …`, `fix(model): …` (or path-filtered commits under `modules/model/`). Title style `feat/PPT-024: …` alone does **not** drive a version bump.

**Why `workflow_call`:** tags created with `GITHUB_TOKEN` inside Actions often **do not** start other `on: push: tags` workflows. Calling publish from the release job avoids that cascade gap. Manual tag pushes (human/PAT) and `workflow_dispatch` remain as escape hatches.

### Publish model package (PPT-024)

|             |                                                                                                                                                                                                                                                                                                                                |
| :---------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Trigger** | `workflow_call` (from release / dev); tag `model-v*` → PyPI; `workflow_dispatch` with `target=testpypi` \| `pypi`                                                                                                                                                                                                              |
| **Package** | `papita-transactions-model` (`./bin/package.sh --mod model`)                                                                                                                                                                                                                                                                   |
| **Auth**    | GitHub OIDC → PyPI **Trusted Publisher** (environments `testpypi` / `pypi`). Publish steps set `attestations: false` because PEP 740 attestations use the **caller** workflow as Build Config URI while the publisher is registered as `publish-model.yml` ([warehouse#11096](https://github.com/pypi/warehouse/issues/11096)) |
| **Gates**   | Tag/ref version must match `modules/model/pyproject.toml` (stable); clean-venv wheel import smoke                                                                                                                                                                                                                              |

**Stable release flow:** merge conventional model commits to `main` → `release-model.yml` tags `model-v*` → **calls** `publish-model.yml` → **PyPI**.

### Publish model (dev) → TestPyPI

|             |                                                                                                                                                                                                                                                                                                    |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Trigger** | Pull request (non-draft, same-repo) with paths under `modules/model/**` (or the publish/dev scripts/workflows listed in the YAML)                                                                                                                                                                  |
| **Gate**    | [`wait_for_pr_checks.sh`](./scripts/wait_for_pr_checks.sh) — all other `pull_request` workflow runs for the head SHA must succeed (**`cancelled` runs ignored** — concurrency / re-trigger supersession); always requires **Secret Scan**, **Branch sync with main**, and **Code Quality Control** |
| **Version** | Ephemeral stamp `{pyproject_version}.dev{github.run_id}` (PEP 440; not committed) via [`stamp_model_dev_version.py`](./scripts/stamp_model_dev_version.py)                                                                                                                                         |
| **Publish** | Reuses `publish-model.yml` (`workflow_call`, `target=testpypi`, `stamp_dev_version=true`). Publish jobs key off `inputs.target` — not `github.event_name == workflow_call` (inside a called workflow that name is the **caller** event, e.g. `pull_request`)                                       |
| **Cadence** | Every qualifying PR push (`synchronize`); concurrency cancels in-progress runs for the same PR                                                                                                                                                                                                     |
| **Skipped** | Draft PRs; fork PRs; PRs with no `modules/model/**` (path filter); `publish-pypi` on this path (TestPyPI only)                                                                                                                                                                                     |

```bash
# Install a PR preview build from TestPyPI (pin the stamped version from the Actions summary)
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "papita-transactions-model==<version>.dev<run_id>"
```

**Operator setup (once):** on [TestPyPI](https://test.pypi.org/) / [PyPI](https://pypi.org/), add a Trusted Publisher for this repository, workflow **`publish-model.yml`** (the reusable file that performs OIDC), and the matching environment. For PR → TestPyPI, the `testpypi` GitHub Environment must allow deployments from PR head branches (not only `main`). Prefer environment protection on `pypi`. Do not store long-lived tokens in git.

**Local:** `make package-model` · docs: [`modules/model/README.md`](../modules/model/README.md) § Install.

---

### Code Quality Control

|               |                                                                  |
| :------------ | :--------------------------------------------------------------- |
| **Trigger**   | PR opened/synchronized/reopened; `paths-ignore: docs/**`         |
| **Runner**    | `ubuntu-latest`                                                  |
| **Artifacts** | `docs/coverage.xml` (Codecov upload when `CODECOV_TOKEN` is set) |

**Steps:**

1. Checkout → Python 3.12 → Poetry 2.1.3 → `poetry install --no-interaction`
2. Install extra CI tools: `pylint`, `pytest`, `pytest-cov`, `coverage`
3. **pre-commit** ([`pre-commit/action@v3.0.0`](https://github.com/pre-commit/action)) — all hooks from [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) **except** local-only hooks:

   ```yaml
   SKIP: strata-validate,mcp-config-validate,web-eslint,web-prettier,web-tsc,web-vitest-related
   ```

4. **Pytest + coverage** via [`bin/test.sh`](../bin/test.sh)
   - `testpaths`: `modules/model/tests`, `modules/api/tests`
   - Coverage measured on **source packages**: `--cov=./modules/model/src --cov=./modules/api/src` (aligned with Codecov)
   - Env: `AUTH_PROVIDER=local` (Supabase is Auth-only; JWT smoke is manual: `make auth-smoke`)
   - Coverage XML: `docs/coverage.xml`
5. Codecov upload — **skipped** when `CODECOV_TOKEN` is unset; when set, uploads `docs/coverage.xml` with flag `unittests` per root [`codecov.yml`](../codecov.yml) (`fail_ci_if_error: true`). Validate YAML: `curl --data-binary @codecov.yml https://codecov.io/validate`

**Supabase (Auth only):** no CI job hits Supabase Postgres. Staging Auth is validated with `make auth-smoke` against a running API (`AUTH_PROVIDER=supabase` + `SUPABASE_*`). Application data always uses Docker / app Postgres (B0).

**Code style enforced here:** Black (120 cols), isort (black profile), flake8, pylint, mypy (gradual), interrogate (≥90% doc coverage on `modules/*/src`), shellcheck, yamllint, markdownlint, actionlint, prettier. Configuration lives in [`pyproject.toml`](../pyproject.toml) and [`.cursor/rules/gen-custom/`](../.cursor/rules/gen-custom/).

---

### Migration Check

|             |                                                                                                    |
| :---------- | :------------------------------------------------------------------------------------------------- |
| **Trigger** | PR + push to `main` when paths under model schema, Alembic, Docker DB, or migration scripts change |
| **Service** | PostgreSQL 15 (`papita` / `papita` / `papita_test`, port 5432)                                     |

**Path filters:**

- `modules/model/alembic/**`
- `modules/model/src/papita_txnsmodel/model/**`
- `docker/database/**`
- `bin/alembic.sh`
- `.github/scripts/migration_check.sh`
- `.github/workflows/migration-check.yml`

**Script:** [`scripts/migration_check.sh`](./scripts/migration_check.sh) — requires `DB_URL`.

| Step | Alembic command | Purpose                        |
| :--- | :-------------- | :----------------------------- |
| 1    | `upgrade head`  | Apply all migrations           |
| 2    | `downgrade -1`  | Verify reversibility           |
| 3    | `upgrade head`  | Round-trip restore             |
| 4    | `check`         | Detect model ↔ migration drift |

**Local shortcuts:**

```bash
# Docker Postgres via bin/ wrapper (upgrade only — not the full CI round-trip)
/bin/bash ./bin/alembic.sh upgrade --docker-local --docker-rm

# Full CI parity (Postgres must be reachable)
export DB_URL="postgresql+psycopg2://user:pass@localhost:5432/papita_transactions"
/bin/bash .github/scripts/migration_check.sh
```

---

### Supply Chain Check

|               |                                                                            |
| :------------ | :------------------------------------------------------------------------- |
| **Trigger**   | PR + push on dependency/workflow paths; Mon 08:00 UTC; `workflow_dispatch` |
| **Lock file** | Not required — `poetry.lock` is gitignored                                 |

**Path filters:** `pyproject.toml`, `modules/**/pyproject.toml`, `.github/scripts/*.{sh,py}`, `.github/workflows/*.yml`

**Script:** [`scripts/supply_chain_check.sh`](./scripts/supply_chain_check.sh)

| Step | Command                               | Purpose                                                 |
| :--- | :------------------------------------ | :------------------------------------------------------ |
| 1    | `poetry check`                        | Validate workspace and module `pyproject.toml` metadata |
| 2    | `check_module_versions.py`            | Each module has a valid semver in `[project].version`   |
| 3    | `pip install --upgrade 'pip>=26.1.2'` | Patched pip before audit                                |
| 4    | `pip-audit --desc on --skip-editable` | Known CVEs in installed dependencies                    |

---

### Secret Scan (Gitleaks)

|                 |                                                                    |
| :-------------- | :----------------------------------------------------------------- |
| **Trigger**     | Every PR; every push to `main`; Mon 05:00 UTC; `workflow_dispatch` |
| **Scope**       | Full git history (`fetch-depth: 0`)                                |
| **Permissions** | `contents: read`                                                   |

**Configuration:** [`.gitleaks.toml`](../.gitleaks.toml) — extends default rules; allowlists `.env.example` and documented placeholder strings (`changeme`, `<password>`, etc.).

**Action:** [`gitleaks/gitleaks-action@v3`](https://github.com/gitleaks/gitleaks-action) (SHA-pinned in workflow).

Findings appear in workflow logs, not the Security tab SARIF view.

---

### CodeQL Python

|                 |                                                                                      |
| :-------------- | :----------------------------------------------------------------------------------- |
| **Trigger**     | PRs **targeting `main`**; push to `main`; Mon 06:00 UTC; `workflow_dispatch`         |
| **Paths**       | `modules/model/**`, `modules/api/**`, root/`modules/*/pyproject.toml`, workflow file |
| **Timeout**     | 30 minutes                                                                           |
| **Permissions** | `security-events: write` (Security tab)                                              |
| **Concurrency** | `codeql-python-${{ github.ref }}` (does **not** share a group with JS/TS CodeQL)     |

- **Language:** Python only (no JS/TS matrix)
- **Queries:** `security-extended`
- **Build:** `poetry install` before analysis so imports resolve
- **Independence:** JavaScript/TypeScript uses a separate workflow ([`codeql-javascript.yml`](./workflows/codeql-javascript.yml))

### CodeQL JavaScript/TypeScript

|                 |                                                                                     |
| :-------------- | :---------------------------------------------------------------------------------- |
| **Trigger**     | PRs **targeting `main`**; push to `main`; Mon 06:30 UTC; `workflow_dispatch`        |
| **Paths**       | `modules/web/**`, pnpm lock/workspace, root `package.json`, `.nvmrc`, workflow file |
| **Timeout**     | 30 minutes                                                                          |
| **Permissions** | `security-events: write` (Security tab)                                             |
| **Concurrency** | `codeql-javascript-${{ github.ref }}`                                               |

- **Language:** `javascript-typescript`
- **Queries:** `security-extended`
- **Build:** `pnpm install --frozen-lockfile` (Node from `.nvmrc`, pnpm 9.15.9) before analysis
- **Independence:** Does not install Poetry or run the Python CodeQL job; SARIF category `/language:javascript-typescript`

---

### Trivy Security Scan

|             |                                                                        |
| :---------- | :--------------------------------------------------------------------- |
| **Trigger** | PR + push on manifest/docker paths; Mon 07:00 UTC; `workflow_dispatch` |
| **Timeout** | 15 minutes                                                             |

**Path filters:** `pyproject.toml`, `modules/**/pyproject.toml`, `docker/**`, workflow file.

| Setting       | Value                                               |
| :------------ | :-------------------------------------------------- |
| Scan type     | Filesystem (`.`)                                    |
| Scanners      | `vuln`, `misconfig`                                 |
| Severity gate | CRITICAL, HIGH (`exit-code: 1`)                     |
| Unfixed CVEs  | Ignored (`ignore-unfixed: true`)                    |
| Output        | SARIF → Security tab (`category: trivy-filesystem`) |

---

### Bash Security

|                 |                                                         |
| :-------------- | :------------------------------------------------------ |
| **Trigger**     | **PR only** (no push, schedule, or `workflow_dispatch`) |
| **Timeout**     | 10 min (ShellCheck) / 15 min (Semgrep)                  |
| **Permissions** | `contents: read`                                        |

**Path filters:** `bin/**`, `.github/scripts/**`, `.github/semgrep/**`, workflow file.

| Job                     | Tool                                                                                                                 | Scope                                                                                                                                      |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| ShellCheck (security)   | [`ludeeus/action-shellcheck@2.0.0`](https://github.com/ludeeus/action-shellcheck) (SHA-pinned), ShellCheck `v0.11.0` | Include-only codes: `SC2046`, `SC2048`, `SC2068`, `SC2086`, `SC2115`, `SC2145`, `SC2154`, `SC2164`, `SC2206`, `SC2207`, `SC2294`, `SC2479` |
| Semgrep (bash security) | `semgrep/semgrep:1.128.1` (digest-pinned)                                                                            | Local [`.github/semgrep/bash-security.yml`](./semgrep/bash-security.yml) + `p/trailofbits`; `bin/` + `.github/scripts/`                    |

**Intentionally not in this workflow:** Trivy, CodeQL, Gitleaks (already covered elsewhere). Full ShellCheck style remains in pre-commit / Quality Control.

**Note:** Registry pack `p/bash` is unavailable (404); bash coverage uses custom rules plus Trail of Bits multilang rules that apply to `.sh` files.

---

### Strata Check

|             |                                                                        |
| :---------- | :--------------------------------------------------------------------- |
| **Trigger** | **PR only** (no push-to-main job)                                      |
| **Paths**   | `modules/**`, `pyproject.toml`, `bin/**`, strata script/workflow files |

**Not triggered by:** `.strata/**`-only changes — use local pre-commit or run `strata_check.sh` manually.

**Environment:**

```bash
STRATA_STRICT_MODULES=1
STRATA_BASE_REF=origin/<base_branch>   # e.g. origin/main
```

See [Strata validation](#strata-validation) for the full rule set.

---

### Auto Updates

|                 |                                                          |
| :-------------- | :------------------------------------------------------- |
| **Trigger**     | Push to `main`, or PR merged into `main`                 |
| **Permissions** | `contents: write`, `issues: read`, `pull-requests: read` |

**Steps:**

1. [`update_todos.py`](./scripts/update_todos.py) — rebuild [`CHANGELOG.md`](../CHANGELOG.md) from GitHub issues/PRs (Jinja templates in `scripts/`)
2. [`sync_coverage_badge.py`](./scripts/sync_coverage_badge.py) — fetch latest totals from [Codecov](https://app.codecov.io/github/Elmorralito/save-ma-money) and regenerate `docs/coverage-badge.svg` via `genbadge` (polls until the current commit is processed). Uses the public Codecov API v2 for this public repo; optional `CODECOV_API_TOKEN` (Codecov **Settings → Access**) only if authenticated reads are needed. **Do not** pass `CODECOV_TOKEN` (upload token) to this step — it returns 401 on read endpoints.
3. Regenerate `docs/flake8-badge.svg` via `genbadge`
4. Commit changed files; push with `[skip ci]` message and `ci.skip` option to avoid recursive workflow runs

**Files committed:** `CHANGELOG.md`, `README.md`, `docs/coverage-badge.svg`, `docs/flake8-badge.svg`

---

### CI Adoption Badge

|                 |                                                         |
| :-------------- | :------------------------------------------------------ |
| **Trigger**     | PR + push to `main`; Mon 06:00 UTC; `workflow_dispatch` |
| **Permissions** | `contents: write`                                       |
| **Script**      | [`evaluate_ci.py`](./scripts/evaluate_ci.py)            |

**Steps:**

1. Evaluate CI configuration files and quality signals; write `badge_url`, `level`, `score`, and `tools` to step outputs
2. Replace the `CI Adoption` badge placeholder in [`README.md`](../README.md)
3. Commit with `ci: update CI adoption badge [skip ci]` via `stefanzweifel/git-auto-commit-action@v5`
4. Emit a step summary with level, score, detected tools, and quality signals

**Loop guard:** push jobs skip when the head commit message contains `[skip ci]`.

**Expected baseline for this repo:** **77** (**Advanced**) with the v2 rubric — semantic workflow keywords, eight config quality signals, and six runtime signals (Postgres CI, live DB tests, Codecov gate, pip-audit, scheduled QC, Strata push gate). Quality-control runs on PR, push to `main`, and weekly schedule with Postgres live integration tests.

See [CI Adoption Badge](#ci-adoption-badge) for the scoring rubric and local usage.

### Branch protection (recommended)

`main` is not branch-protected today. To require the quality gate before merge:

1. GitHub → **Settings → Branches → Add rule** for `main`
2. Enable **Require status checks to pass**
3. Required checks: **Code Quality Control**, **Secret Scan** (minimum); add **Strata Check**, **Migration Check**, **Supply Chain Check** when path filters apply
4. Enable **Require branches to be up to date**

Or via CLI (repo admin):

```bash
gh api repos/Elmorralito/save-ma-money/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Code Quality Control","Secret Scan"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null
```

---

## CI Adoption Badge

The [`ci-badge.yml`](./workflows/ci-badge.yml) workflow maintains a dynamic shields.io badge in `README.md` that reflects repository CI maturity. Detection is **config-file based** for quality signals and **content-semantic** for workflow keywords (v2).

### Scoring rubric (v2)

**Total = min(GitHub Actions + quality signals + runtime signals, 100)**

| Layer             | Signal                                                                                       |           Points | Detection                                                                      |
| :---------------- | :------------------------------------------------------------------------------------------- | ---------------: | :----------------------------------------------------------------------------- |
| CI platform       | GitHub Actions presence                                                                      |              +20 | `.github/workflows/*.yml` exist                                                |
| Workflow keywords | `test`, `lint`, `deploy`, `security`, `coverage`                                             | +1 each per file | Semantic regex in workflow YAML (v2 — ignores `ubuntu-latest` false positives) |
| Config            | Test coverage, linting, pre-commit, Dependabot, security scans, Docker, bin/ scripts, Strata |          +33 max | File/config presence (same as v1)                                              |
| **Runtime**       | Postgres CI service                                                                          |               +2 | `quality-control.yml` has `services.postgres`                                  |
| **Runtime**       | Live DB integration tests                                                                    |               +2 | QC sets `DATABASE_URL`, runs Alembic + `bin/test.sh`                           |
| **Runtime**       | Codecov upload gate                                                                          |               +1 | `fail_ci_if_error: true` when `CODECOV_TOKEN` is configured                    |
| **Runtime**       | Supply chain audit                                                                           |               +1 | `pip-audit` in `supply_chain_check.sh`                                         |
| **Runtime**       | Scheduled quality control                                                                    |               +1 | `schedule` cron in QC workflow                                                 |
| **Runtime**       | Strata push gate                                                                             |               +1 | `strata-check.yml` runs on push to `main`                                      |

**Levels:** Advanced ≥ 75 · Intermediate ≥ 50 · Basic ≥ 20 · None &lt; 20

### Scoring rubric (v1 — superseded)

| Signal                                                             | Base points      | Bonus                                                                               |
| :----------------------------------------------------------------- | :--------------- | :---------------------------------------------------------------------------------- |
| GitHub Actions (`.github/workflows/*.yml`)                         | +20              | +1 per keyword substring in YAML (`test`, `lint`, `deploy`, `security`, `coverage`) |
| Travis / CircleCI / Jenkins / GitLab CI                            | +15 each         | +1 per keyword                                                                      |
| Azure / Bitbucket / Drone / TeamCity / Buildkite                   | +10 each         | +1 per keyword                                                                      |
| Test coverage config                                               | +5               | —                                                                                   |
| Linting config (`.flake8`, `.pylintrc`, `pyproject` tool sections) | +5               | —                                                                                   |
| Pre-commit hooks                                                   | +5               | —                                                                                   |
| Dependabot                                                         | +5               | —                                                                                   |
| Security scanning workflows                                        | +5               | —                                                                                   |
| Docker support                                                     | +3               | —                                                                                   |
| Ops automation (`bin/` or `Makefile`)                              | +2               | —                                                                                   |
| Strata layout (`.strata/`)                                         | +3               | repo-specific bonus                                                                 |
| **Maximum**                                                        | **100** (capped) |                                                                                     |

### Triggers

| Event               | When it runs                                  |
| :------------------ | :-------------------------------------------- |
| `push`              | Commits to `main` (skips `[skip ci]` commits) |
| `pull_request`      | PRs targeting `main`                          |
| `schedule`          | Mondays at 06:00 UTC (`0 6 * * 1`)            |
| `workflow_dispatch` | Manual run from the Actions tab               |

### Run locally

```bash
python .github/scripts/evaluate_ci.py
python .github/scripts/evaluate_ci.py --update-readme
```

`REPO_NAME` defaults to `owner/repo`; set it to `Elmorralito/save-ma-money` for the correct badge link target.

**Local pre-push feedback (optional):** install the advisory hook once, then every `git push` prints the adoption report without blocking:

```bash
pre-commit install --hook-type pre-push
```

The hook uses [`pre_commit_ci_adoption.sh`](./scripts/pre_commit_ci_adoption.sh) (`stages: [pre-push]` only — not run by CI pre-commit).

### Manual refresh

Open **Actions → CI Adoption Badge → Run workflow** (`workflow_dispatch`) after CI changes land on `main`.

---

## Pre-commit hooks

Defined in [`.pre-commit-config.yaml`](../.pre-commit-config.yaml). CI runs all hooks **except** the two local-only entries below.

### Hook inventory

| Hook                      | Source                          | Scope / notes                                                      |
| :------------------------ | :------------------------------ | :----------------------------------------------------------------- |
| `trailing-whitespace`     | pre-commit-hooks v6.0.0         | All files                                                          |
| `end-of-file-fixer`       | pre-commit-hooks                | All files                                                          |
| `check-yaml`              | pre-commit-hooks                | YAML                                                               |
| `check-toml`              | pre-commit-hooks                | TOML                                                               |
| `detect-private-key`      | pre-commit-hooks                | Blocks committed private keys                                      |
| `check-added-large-files` | pre-commit-hooks                | Max 1024 KB per file                                               |
| `prettier`                | mirrors-prettier v4.0.0-alpha.8 | yaml, python, toml, json, markdown; excludes `*.svg`               |
| `shellcheck`              | shellcheck-precommit v0.11.0    | Shell scripts                                                      |
| `isort`                   | isort 6.1.0                     | Python (black profile); excludes tests                             |
| `black`                   | black 26.3.1                    | Python; excludes tests                                             |
| `flake8`                  | flake8 7.3.0                    | Config from `pyproject.toml` (120 cols, complexity 18)             |
| `pylint`                  | local                           | `poetry run pylint`; serial execution                              |
| `mypy`                    | mirrors-mypy v1.18.2            | Gradual typing; excludes tests                                     |
| `interrogate`             | interrogate 1.7.0               | Docstring coverage ≥90% on `modules/*/src`; badge → `docs/`        |
| `markdownlint`            | markdownlint-cli v0.45.0        | `--fix`; MD013/033/041/024/025 disabled                            |
| `yamllint`                | yamllint v1.37.1                | `*.yaml`, `*.yml`                                                  |
| `actionlint`              | actionlint v1.7.7               | GitHub Actions workflow syntax                                     |
| **`strata-validate`**     | **local only**                  | See [Strata validation](#strata-validation)                        |
| **`mcp-config-validate`** | **local only**                  | See [MCP config](#mcp-config-local)                                |
| **`ci-adoption-check`**   | **local pre-push, advisory**    | See [CI Adoption Badge](#ci-adoption-badge)                        |
| **`web-eslint`**          | **local only**                  | ESLint `--fix --max-warnings=0` on staged `modules/web` TS/JS      |
| **`web-prettier`**        | **local only**                  | Prettier write via `modules/web` config on staged web files        |
| **`web-tsc`**             | **local only**                  | `tsc -b --pretty false` when any `modules/web` `.ts`/`.tsx` staged |
| **`web-vitest-related`**  | **local only**                  | `vitest related --run` for staged web TS files                     |

### Local-only hooks

| Hook ID               | Wrapper                                                            | When it runs                                                                         |
| :-------------------- | :----------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| `strata-validate`     | [`pre_commit_strata.sh`](./scripts/pre_commit_strata.sh)           | **Always runs** on commit; evaluates **all staged paths** via `git diff --cached`    |
| `mcp-config-validate` | [`pre_commit_mcp.sh`](./scripts/pre_commit_mcp.sh)                 | Staged `.cursor/mcp.json`                                                            |
| `ci-adoption-check`   | [`pre_commit_ci_adoption.sh`](./scripts/pre_commit_ci_adoption.sh) | `git push` when `pre-commit install --hook-type pre-push` is set                     |
| `web-eslint`          | [`pre_commit_web.sh`](./scripts/pre_commit_web.sh) `eslint`        | Staged `modules/web/**/*.{ts,tsx,js,jsx}`                                            |
| `web-prettier`        | [`pre_commit_web.sh`](./scripts/pre_commit_web.sh) `prettier`      | Staged web `ts/tsx/js/jsx/css/json/md` (uses package Prettier, not mirrors-prettier) |
| `web-tsc`             | [`pre_commit_web.sh`](./scripts/pre_commit_web.sh) `tsc`           | When any `modules/web` TypeScript file is staged                                     |
| `web-vitest-related`  | [`pre_commit_web.sh`](./scripts/pre_commit_web.sh) `test`          | Related Vitest files only (not the full suite)                                       |

Wrappers for Strata/MCP/web **exit 0 immediately** when `CI` or `GITHUB_ACTIONS` is set (belt-and-suspenders alongside `SKIP` in quality-control). `ci-adoption-check` uses `stages: [pre-push]` only, so CI pre-commit never invokes it. Web CI remains [`.github/workflows/web-ci.yml`](./workflows/web-ci.yml).

---

## Strata validation

[`strata_check.sh`](./scripts/strata_check.sh) enforces [belousov-petr/strata](https://github.com/belousov-petr/strata) `layout_version: 3`. It validates structure and frontmatter — it does **not** run `/strata:save`.

### Layout requirements

**Required files:** `MANIFEST.md`, `memory/MEMORY.md`, `memory/project_state.md`, learnings index/template, archive files, issue views (`ACTIVE.md`, `OPEN.md`, `PARKED.md`), `docs/ARCHITECTURE.md`, `inbox/.gitignore`, plus `.agents/AGENTS.md` and `.agents/CLAUDE.md`.

**Required directories:** `memory/learnings`, `memory/archive`, `docs/{product,architecture,decisions,reference,ops}`, `inbox`. (Closed issues are deleted from `.strata/issues/` — no `issues/archive/`.)

### Content rules

| Rule                      | Limit / values                                     |
| :------------------------ | :------------------------------------------------- |
| `MANIFEST.md` frontmatter | `layout_version: 3`                                |
| Adapter files             | Must reference `.strata/MANIFEST.md`               |
| Template placeholders     | No `{{PROJECT_NAME}}` or `{{INIT_DATE}}` remaining |
| `memory/MEMORY.md`        | ≤ 80 lines                                         |
| `memory/project_state.md` | ≤ 200 lines                                        |

### Issue item frontmatter

Files matching `.strata/issues/[0-9]*-*.md`:

| Field                 | Allowed values                                                |
| :-------------------- | :------------------------------------------------------------ |
| `type`                | `bug`, `improvement`, `debt`, `task`, `feature`, `initiative` |
| `status`              | `open`, `in-progress`, `parked`, `resolved`, `wont-fix`       |
| `severity` (optional) | `high`, `med`, `low`                                          |
| `revive-when`         | Required when `status: parked`                                |

### Strict mode (code ↔ memory pairing + code review)

When `STRATA_STRICT_MODULES=1`:

| Context               | Diff source                     | Behavior                                                                                                              |
| :-------------------- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------------- |
| **Local pre-commit**  | `STRATA_DIFF_SOURCE=staged`     | Staged `modules/**` or `bin/**` must include `.strata/**`, `.agents/**`, or `.cursor/AGENTS.md` / `.cursor/CLAUDE.md` |
| **CI (Strata Check)** | `STRATA_BASE_REF=origin/<base>` | Same rule across the PR diff vs base branch                                                                           |

When `STRATA_CODE_REVIEW=1` (default in strict mode), changed files under `modules/**`, `bin/**`, or `.github/scripts/**` are reviewed via [`strata_code_review.sh`](./scripts/strata_code_review.sh):

| Language | Hooks (pre-commit)                           |
| :------- | :------------------------------------------- |
| Python   | `black`, `isort`, `flake8`, `pylint`, `mypy` |
| Bash     | `shellcheck`                                 |

Disable review only: `STRATA_CODE_REVIEW=0`. Strata Check installs Poetry + pre-commit deps before running the review in CI.

**Fix workflow:** `/strata:capture` during work → `/strata:save` before push → `git add .strata/ .agents/AGENTS.md .agents/CLAUDE.md` → commit again.

---

## MCP config (local)

[`mcp_config_check.sh`](./scripts/mcp_config_check.sh) runs when `.cursor/mcp.json` exists:

1. Valid JSON
2. Root is an object; `mcpServers` (if present) is an object of server configs
3. Each server defines a non-empty `url` **or** `command`
4. No hardcoded token patterns (GitHub PAT, OpenAI `sk-`, Slack, AWS access keys)

Missing file → skip with success (project may not use MCP).

---

## Supporting scripts

| Script                                                               | Invoked by               | Description                                                              |
| :------------------------------------------------------------------- | :----------------------- | :----------------------------------------------------------------------- |
| [`branch_sync_check.sh`](./scripts/branch_sync_check.sh)             | Branch sync with main    | Fail if `HEAD` is behind `BASE_REF` (default `origin/main`)              |
| [`wait_for_pr_checks.sh`](./scripts/wait_for_pr_checks.sh)           | Publish model (dev)      | Poll Actions until other PR checks for `COMMIT_SHA` succeed              |
| [`stamp_model_dev_version.py`](./scripts/stamp_model_dev_version.py) | Publish model (dev)      | Rewrite model `project.version` to `{base}.dev{run_id}` for TestPyPI     |
| [`migration_check.sh`](./scripts/migration_check.sh)                 | Migration Check          | Alembic upgrade → downgrade → upgrade → `check`; requires `DB_URL`       |
| [`supply_chain_check.sh`](./scripts/supply_chain_check.sh)           | Supply Chain Check       | Poetry metadata, semver check, pip upgrade, pip-audit                    |
| [`check_module_versions.py`](./scripts/check_module_versions.py)     | Supply Chain Check       | Validates `[project].version` semver in each `modules/*/pyproject.toml`  |
| [`strata_check.sh`](./scripts/strata_check.sh)                       | Strata Check, pre-commit | Layout, budgets, frontmatter, strict pairing                             |
| [`pre_commit_strata.sh`](./scripts/pre_commit_strata.sh)             | pre-commit               | Sets `STRATA_STRICT_MODULES=1`, `STRATA_DIFF_SOURCE=staged`; skips in CI |
| [`mcp_config_check.sh`](./scripts/mcp_config_check.sh)               | pre-commit               | MCP JSON structure + token scan                                          |
| [`pre_commit_mcp.sh`](./scripts/pre_commit_mcp.sh)                   | pre-commit               | CI skip wrapper for MCP check                                            |
| [`pre_commit_ci_adoption.sh`](./scripts/pre_commit_ci_adoption.sh)   | pre-push (local)         | Advisory CI adoption report; never blocks push                           |
| [`update_todos.py`](./scripts/update_todos.py)                       | Auto Updates             | CHANGELOG from GitHub API                                                |
| [`evaluate_ci.py`](./scripts/evaluate_ci.py)                         | CI Adoption Badge        | CI tool detection, adoption scoring, README badge metadata               |
| [`changelog_template.jinja`](./scripts/changelog_template.jinja)     | update_todos.py          | CHANGELOG section template                                               |
| [`issue_template.jinja`](./scripts/issue_template.jinja)             | update_todos.py          | Per-issue CHANGELOG entry template                                       |

Shared shell helpers: [`bin/utils.sh`](../bin/utils.sh) (`log`, `run_command`).

---

## PR checklist

Before opening or marking a PR ready:

```bash
pre-commit run --all-files
/bin/bash ./bin/test.sh
```

**When paths change, also run:**

| If you changed…                         | Also run                                                       |
| :-------------------------------------- | :------------------------------------------------------------- |
| `pyproject.toml` or module dependencies | `/bin/bash .github/scripts/supply_chain_check.sh`              |
| SQLModel classes or Alembic revisions   | `/bin/bash .github/scripts/migration_check.sh` (with `DB_URL`) |
| Architecture, backlog, or agent memory  | `/strata:save` then verify with `strata_check.sh`              |
| `.cursor/mcp.json`                      | `/bin/bash .github/scripts/mcp_config_check.sh`                |

**Always:**

- Never commit `.env`, credentials, or real secrets
- Pair `modules/**` / `bin/**` edits with `.strata/` (or adapter) updates
- Keep the branch current with `main` (`git fetch origin && git merge origin/main` — Branch sync CI gate)
- Keep PR scope focused
- Use the PR body template: [`.github/PULL_REQUEST_TEMPLATE.md`](./PULL_REQUEST_TEMPLATE.md)
- New issues: use [`.github/ISSUE_TEMPLATE/`](./ISSUE_TEMPLATE/) (epic / program / child / bug)

Full agent-oriented checklist: [`.agents/AGENTS.md` — PR checklist](../.agents/AGENTS.md#pr-checklist).

---

## Troubleshooting

### Branch sync failed: behind `origin/main`

```
Branch is N commit(s) behind origin/main
```

Your PR head is missing commits that landed on `main`. Update and push:

```bash
git fetch origin
git merge origin/main   # or: git rebase origin/main
git push
```

Local preview: `/bin/bash .github/scripts/branch_sync_check.sh`

### Strata Check / `strata-validate` failed: code without memory update

```
code paths changed but .strata/ (or .agents/AGENTS.md / .agents/CLAUDE.md) was not updated
```

Run `/strata:save`, stage `.strata/`, `.agents/AGENTS.md`, and/or `.agents/CLAUDE.md`, recommit.

### Strata Check did not run on my PR

The workflow path filter excludes `.strata/**`. It runs when `modules/**`, `bin/**`, or root `pyproject.toml` change. For memory-only edits, rely on local pre-commit or run `strata_check.sh` manually before pushing.

### `strata_check.sh`: base ref not available locally

Fetch the default branch: `git fetch origin main`. Or set `STRATA_BASE_REF` to a ref that exists locally.

### Migration Check: connection refused

Ensure PostgreSQL is reachable at the URL in `DB_URL`. CI uses a service container; locally start Docker Compose from [`docker/database/`](../docker/database/) or point `DB_URL` at your instance.

### `pip-audit` reports a CVE

1. Check if a patched version exists upstream
2. Bump the dependency in the relevant `pyproject.toml`
3. Re-run `/bin/bash .github/scripts/supply_chain_check.sh`

### Gitleaks flagged a placeholder

Add a documented placeholder to [`.gitleaks.toml`](../.gitleaks.toml) allowlist regexes, or move the value to an env var / secret store.

### Trivy CRITICAL/HIGH on a dependency

Review the SARIF entry in **Security → Code scanning**. If a fix is unavailable (`ignore-unfixed: true` may still pass when no patch exists), document the accepted risk or pin/override the dependency.

### Quality Control skipped on docs-only PR

Expected — `paths-ignore: docs/**`. Gitleaks still runs.

### pre-commit reformatted files

Re-stage and commit. Hooks like Black, prettier, and markdownlint `--fix` modify files in place.

---

## Scheduled scans

All times **UTC**, every **Monday**:

| Workflow            | Cron         | Local time hint (US Eastern, DST) |
| :------------------ | :----------- | :-------------------------------- |
| Secret Scan         | `0 5 * * 1`  | ~01:00 EDT                        |
| CI Adoption Badge   | `0 6 * * 1`  | ~02:00 EDT                        |
| CodeQL Python       | `0 6 * * 1`  | ~02:00 EDT                        |
| CodeQL JS/TS        | `30 6 * * 1` | ~02:30 EDT                        |
| Trivy Security Scan | `0 7 * * 1`  | ~03:00 EDT                        |
| Supply Chain Check  | `0 8 * * 1`  | ~04:00 EDT                        |

Each scheduled workflow also supports **`workflow_dispatch`** from the Actions tab. Bash Security is **PR-only** (not scheduled).

---

## Security tab integration

| Source                             | Location                        | Format                              |
| :--------------------------------- | :------------------------------ | :---------------------------------- |
| CodeQL (Python + JS/TS workflows)  | Security → Code scanning alerts | Native CodeQL (separate categories) |
| Trivy                              | Security → Code scanning alerts | SARIF (`trivy-filesystem`)          |
| Gitleaks                           | Workflow job logs               | Inline findings                     |
| Bash Security (ShellCheck/Semgrep) | Workflow job logs               | Inline findings (fails the job)     |
| pip-audit                          | Supply Chain Check logs         | Text report with CVE descriptions   |
| pre-commit `detect-private-key`    | Local / Quality Control logs    | Blocks commit/CI                    |

---

## Environment variables

| Variable                  | Used by                             |          Required          | Example                                                          |
| :------------------------ | :---------------------------------- | :------------------------: | :--------------------------------------------------------------- |
| `DB_URL`                  | `migration_check.sh`                |   Yes (migration checks)   | `postgresql+psycopg2://papita:papita@localhost:5432/papita_test` |
| `STRATA_STRICT_MODULES`   | `strata_check.sh`                   |      No (default `0`)      | `1` enables code/memory pairing                                  |
| `STRATA_DIFF_SOURCE`      | `strata_check.sh`                   |    No (default `range`)    | `staged` for pre-commit                                          |
| `STRATA_BASE_REF`         | `strata_check.sh` (CI)              | No (default `origin/main`) | `origin/main`                                                    |
| `CI` / `GITHUB_ACTIONS`   | pre-commit wrappers                 |         Set by GHA         | Skips local-only hooks                                           |
| `SKIP`                    | quality-control pre-commit step     |      Set by workflow       | `strata-validate,mcp-config-validate`                            |
| `GITHUB_TOKEN`            | Gitleaks, Auto Updates              |      Provided by GHA       | —                                                                |
| `REPO_OWNER`, `REPO_NAME` | `update_todos.py`, `evaluate_ci.py` |      Set by workflow       | —                                                                |

---

## Toolchain pins

| Component                 | Pin                                               |
| :------------------------ | :------------------------------------------------ |
| Python                    | 3.12                                              |
| Poetry                    | 2.1.3 (`snok/install-poetry@v1`)                  |
| PostgreSQL (migration CI) | `postgres:15-alpine`                              |
| checkout                  | `actions/checkout@v7`                             |
| setup-python              | `actions/setup-python@v7`                         |
| upload-artifact           | `actions/upload-artifact@v6` (Node.js 24)         |
| download-artifact         | `actions/download-artifact@v7` (Node.js 24)       |
| pre-commit action         | `pre-commit/action@v3.0.0`                        |
| Codecov                   | `codecov/codecov-action@v4`                       |
| Gitleaks                  | `gitleaks/gitleaks-action@e0c47f4…` (v3)          |
| CodeQL                    | `github/codeql-action@411c4c9…` (v3 init/analyze) |
| Trivy                     | `aquasecurity/trivy-action@a9c7b0f…` (v0.36.0)    |
| SARIF upload              | `github/codeql-action/upload-sarif@54f647b…` (v4) |
| ShellCheck action         | `ludeeus/action-shellcheck@00cae500…` (2.0.0)     |
| ShellCheck binary         | `v0.11.0` (matches pre-commit)                    |
| Semgrep image             | `semgrep/semgrep:1.128.1@sha256:fca58525…`        |

Action SHAs are pinned in workflow files for supply-chain reproducibility. Bump deliberately and re-run all affected workflows.
