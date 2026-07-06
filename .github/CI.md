# Continuous integration

GitHub Actions workflows, validation scripts, and local pre-commit hooks for **save-ma-money**.

| Constant                  | Value                                                          |
| :------------------------ | :------------------------------------------------------------- |
| Python                    | 3.12                                                           |
| Poetry                    | 2.1.3                                                          |
| PostgreSQL (migration CI) | 15-alpine                                                      |
| Lock file                 | `poetry.lock` is **gitignored** — CI resolves deps at run time |

**Related docs:** [`AGENTS.md`](../AGENTS.md) · [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) · [`.strata/MANIFEST.md`](../.strata/MANIFEST.md) · [Issue #41](https://github.com/Elmorralito/save-ma-money/issues/41) (security CI requirement)

---

## Contents

- [CI at a glance](#ci-at-a-glance)
- [Which checks run on my PR?](#which-checks-run-on-my-pr)
- [Workflow overview](#workflow-overview)
- [Run checks locally](#run-checks-locally)
- [Workflows in detail](#workflows-in-detail)
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
        GL[Secret Scan]
        SC[Supply Chain Check]
        MC[Migration Check]
        CQ[CodeQL Analysis]
        TR[Trivy Security Scan]
        ST[Strata Check]
    end

    subgraph main [Merge to main]
        AU[Auto Updates]
    end

    QC --> |pre-commit + pytest + Codecov| Pass1[Gate]
    GL --> |full history| Pass2[Gate]
    SC --> |poetry check + pip-audit| Pass3[Gate]
    MC --> |Alembic round-trip| Pass4[Gate]
    CQ --> |Python SAST| Pass5[Gate]
    TR --> |CVE + misconfig SARIF| Pass6[Gate]
    ST --> |.strata/ layout + pairing| Pass7[Gate]

    Pass1 & Pass2 & Pass3 & Pass4 & Pass5 & Pass6 & Pass7 --> Merge[Merge]
    Merge --> AU
    AU --> |CHANGELOG + badges| Push[Push to main]
```

**Concurrency:** Most workflows use per-ref concurrency groups and **cancel in-progress** runs when a newer commit lands on the same branch.

**Local vs CI split:** Strata and MCP hooks run on `git commit` locally. GitHub Actions skips them in pre-commit (`SKIP=strata-validate,mcp-config-validate`) and uses dedicated workflows/scripts instead.

---

## Which checks run on my PR?

Use this matrix to predict required checks before opening a PR.

| Change type                                    | Quality Control | Gitleaks | Supply Chain | Migration | CodeQL | Trivy | Strata |
| :--------------------------------------------- | :-------------: | :------: | :----------: | :-------: | :----: | :---: | :----: |
| `docs/**` only                                 |        —        |    ✓     |      —       |     —     |   —    |   —   |   —    |
| `modules/**` code                              |        ✓        |    ✓     |     —\*      |    —\*    |   ✓†   |  —\*  |   ✓    |
| `pyproject.toml` / module deps                 |        ✓        |    ✓     |      ✓       |     —     |   ✓†   |   ✓   |   ✓‡   |
| Model / Alembic / `docker/database/**`         |        ✓        |    ✓     |     —\*      |     ✓     |   ✓†   |  —\*  |   ✓    |
| `.strata/**` only (no `modules/` or `deploy/`) |        ✓        |    ✓     |      —       |     —     |   —    |   —   |   —§   |
| `.github/workflows/**`                         |        ✓        |    ✓     |      ✓       |    —\*    |  —\*   |  —\*  |  —\*   |
| `.cursor/mcp.json`                             |        ✓        |    ✓     |      —       |     —     |   —    |   —   |   —    |

\* Runs only when matching [path filters](#workflow-overview) apply.
† CodeQL runs on PRs **targeting `main`** only.
‡ Strata Check runs when root `pyproject.toml` changes (listed in its path filter).
§ Strata Check path filters do **not** include `.strata/**` — layout validation for memory-only edits is enforced locally via pre-commit, not this workflow.

**Always on PRs:** Secret Scan (Gitleaks) — no path filter, full history.

---

## Workflow overview

| Workflow             | File                                                                     | Triggers                                                   | Purpose                                                 |
| :------------------- | :----------------------------------------------------------------------- | :--------------------------------------------------------- | :------------------------------------------------------ |
| Code Quality Control | [`workflows/quality-control.yml`](./workflows/quality-control.yml)       | PR; skips `docs/**`-only diffs                             | pre-commit, pytest, Codecov                             |
| Migration Check      | [`workflows/migration-check.yml`](./workflows/migration-check.yml)       | PR + push to `main` (model/migration paths)                | PostgreSQL Alembic round-trip + drift check             |
| Supply Chain Check   | [`workflows/supply-chain-check.yml`](./workflows/supply-chain-check.yml) | PR + push (deps/workflow paths); Mon 08:00 UTC             | `poetry check`, version metadata, `pip-audit`           |
| Secret Scan          | [`workflows/gitleaks.yml`](./workflows/gitleaks.yml)                     | **All PRs**; push to `main`; Mon 05:00 UTC                 | Full-history secret detection                           |
| CodeQL Analysis      | [`workflows/codeql.yml`](./workflows/codeql.yml)                         | PR → `main` + push to `main` (`modules/**`); Mon 06:00 UTC | Python SAST (`security-extended`)                       |
| Trivy Security Scan  | [`workflows/trivy.yml`](./workflows/trivy.yml)                           | PR + push (manifest/docker paths); Mon 07:00 UTC           | Filesystem CVE + IaC misconfig (SARIF)                  |
| Strata Check         | [`workflows/strata-check.yml`](./workflows/strata-check.yml)             | **PR only** (code/deploy paths)                            | `.strata/` layout + strict code/memory pairing          |
| Auto Updates         | [`workflows/auto-updates.yml`](./workflows/auto-updates.yml)             | Push or merged PR to `main`                                | Regenerate [`CHANGELOG.md`](../CHANGELOG.md) and badges |

---

## Run checks locally

Mirror CI before pushing:

```bash
# One-shot quality gate (same hooks as CI, plus local Strata/MCP when paths match)
pre-commit run --all-files

# Tests + coverage report → docs/coverage.xml (same entry point as CI)
/bin/bash ./deploy/test.sh

# Supply chain (deps or workflow script changes)
/bin/bash .github/scripts/supply_chain_check.sh

# Strata layout + strict pairing (PR range vs main)
STRATA_STRICT_MODULES=1 STRATA_BASE_REF=origin/main /bin/bash .github/scripts/strata_check.sh

# Strata against staged files only (what pre-commit runs)
/bin/bash .github/scripts/pre_commit_strata.sh

# MCP config (when .cursor/mcp.json exists)
/bin/bash .github/scripts/mcp_config_check.sh

# Migrations — full CI sequence (requires running Postgres)
export DB_URL="postgresql+psycopg2://papita:papita@localhost:5432/papita_test"
/bin/bash .github/scripts/migration_check.sh
```

Install tooling once:

```bash
poetry install --no-interaction
pre-commit install   # optional but recommended for commit-time hooks
```

---

## Workflows in detail

### Code Quality Control

|               |                                                          |
| :------------ | :------------------------------------------------------- |
| **Trigger**   | PR opened/synchronized/reopened; `paths-ignore: docs/**` |
| **Runner**    | `ubuntu-latest`                                          |
| **Artifacts** | `docs/coverage.xml` → Codecov                            |

**Steps:**

1. Checkout → Python 3.12 → Poetry 2.1.3 → `poetry install --no-interaction`
2. Install extra CI tools: `pylint`, `pytest`, `pytest-cov`, `coverage`
3. **pre-commit** ([`pre-commit/action@v3.0.0`](https://github.com/pre-commit/action)) — all hooks from [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) **except** local-only hooks:

   ```yaml
   SKIP: strata-validate,mcp-config-validate
   ```

4. **Pytest + coverage** via [`deploy/test.sh`](../deploy/test.sh)
   - `testpaths`: `modules/model/tests`, `modules/api/tests`, `modules/registrar/tests` (registrar not in tree yet)
   - Coverage XML: `docs/coverage.xml`
5. Codecov upload (`fail_ci_if_error: false`)

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
- `deploy/alembic.sh`
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
# Docker Postgres via deploy wrapper (upgrade only — not the full CI round-trip)
/bin/bash ./deploy/alembic.sh upgrade --docker-local --docker-rm

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

### CodeQL Analysis

|                 |                                                                              |
| :-------------- | :--------------------------------------------------------------------------- |
| **Trigger**     | PRs **targeting `main`**; push to `main`; Mon 06:00 UTC; `workflow_dispatch` |
| **Paths**       | `modules/**`, root `pyproject.toml`, workflow file                           |
| **Timeout**     | 30 minutes                                                                   |
| **Permissions** | `security-events: write` (Security tab)                                      |

- **Language:** Python
- **Queries:** `security-extended`
- **Build:** `poetry install` before analysis so imports resolve

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

### Strata Check

|             |                                                                           |
| :---------- | :------------------------------------------------------------------------ |
| **Trigger** | **PR only** (no push-to-main job)                                         |
| **Paths**   | `modules/**`, `pyproject.toml`, `deploy/**`, strata script/workflow files |

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
2. Regenerate `docs/coverage-badge.svg` and `docs/flake8-badge.svg` via `genbadge`
3. Commit changed files; push with `[skip ci]` message and `ci.skip` option to avoid recursive workflow runs

**Files committed:** `CHANGELOG.md`, `README.md`, `docs/coverage-badge.svg`, `docs/flake8-badge.svg`

---

## Pre-commit hooks

Defined in [`.pre-commit-config.yaml`](../.pre-commit-config.yaml). CI runs all hooks **except** the two local-only entries below.

### Hook inventory

| Hook                      | Source                          | Scope / notes                                               |
| :------------------------ | :------------------------------ | :---------------------------------------------------------- |
| `trailing-whitespace`     | pre-commit-hooks v6.0.0         | All files                                                   |
| `end-of-file-fixer`       | pre-commit-hooks                | All files                                                   |
| `check-yaml`              | pre-commit-hooks                | YAML                                                        |
| `check-toml`              | pre-commit-hooks                | TOML                                                        |
| `detect-private-key`      | pre-commit-hooks                | Blocks committed private keys                               |
| `check-added-large-files` | pre-commit-hooks                | Max 1024 KB per file                                        |
| `prettier`                | mirrors-prettier v4.0.0-alpha.8 | yaml, python, toml, json, markdown; excludes `*.svg`        |
| `shellcheck`              | shellcheck-precommit v0.11.0    | Shell scripts                                               |
| `isort`                   | isort 6.1.0                     | Python (black profile); excludes tests                      |
| `black`                   | black 26.3.1                    | Python; excludes tests                                      |
| `flake8`                  | flake8 7.3.0                    | Config from `pyproject.toml` (120 cols, complexity 18)      |
| `pylint`                  | local                           | `poetry run pylint`; serial execution                       |
| `mypy`                    | mirrors-mypy v1.18.2            | Gradual typing; excludes tests                              |
| `interrogate`             | interrogate 1.7.0               | Docstring coverage ≥90% on `modules/*/src`; badge → `docs/` |
| `markdownlint`            | markdownlint-cli v0.45.0        | `--fix`; MD013/033/041/024/025 disabled                     |
| `yamllint`                | yamllint v1.37.1                | `*.yaml`, `*.yml`                                           |
| `actionlint`              | actionlint v1.7.7               | GitHub Actions workflow syntax                              |
| **`strata-validate`**     | **local only**                  | See [Strata validation](#strata-validation)                 |
| **`mcp-config-validate`** | **local only**                  | See [MCP config](#mcp-config-local)                         |

### Local-only hooks

| Hook ID               | Wrapper                                                  | When it runs                                                              |
| :-------------------- | :------------------------------------------------------- | :------------------------------------------------------------------------ |
| `strata-validate`     | [`pre_commit_strata.sh`](./scripts/pre_commit_strata.sh) | Staged paths: `modules/`, `deploy/`, `.strata/`, `AGENTS.md`, `CLAUDE.md` |
| `mcp-config-validate` | [`pre_commit_mcp.sh`](./scripts/pre_commit_mcp.sh)       | Staged `.cursor/mcp.json`                                                 |

Both wrappers **exit 0 immediately** when `CI` or `GITHUB_ACTIONS` is set (belt-and-suspenders alongside `SKIP` in quality-control).

---

## Strata validation

[`strata_check.sh`](./scripts/strata_check.sh) enforces [belousov-petr/strata](https://github.com/belousov-petr/strata) `layout_version: 3`. It validates structure and frontmatter — it does **not** run `/strata:save`.

### Layout requirements

**Required files:** `MANIFEST.md`, `memory/MEMORY.md`, `memory/project_state.md`, learnings index/template, archive files, issue views (`ACTIVE.md`, `OPEN.md`, `PARKED.md`), `docs/ARCHITECTURE.md`, `inbox/.gitignore`, plus root `AGENTS.md` and `CLAUDE.md`.

**Required directories:** `memory/learnings`, `memory/archive`, `issues/archive`, `docs/{product,architecture,decisions,reference,ops}`, `inbox`.

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

### Strict mode (code ↔ memory pairing)

When `STRATA_STRICT_MODULES=1`:

| Context               | Diff source                     | Behavior                                                                                  |
| :-------------------- | :------------------------------ | :---------------------------------------------------------------------------------------- |
| **Local pre-commit**  | `STRATA_DIFF_SOURCE=staged`     | Staged `modules/**` or `deploy/**` must include `.strata/**`, `AGENTS.md`, or `CLAUDE.md` |
| **CI (Strata Check)** | `STRATA_BASE_REF=origin/<base>` | Same rule across the PR diff vs base branch                                               |

**Fix workflow:** `/strata:capture` during work → `/strata:save` before push → `git add .strata/ AGENTS.md CLAUDE.md` → commit again.

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

| Script                                                           | Invoked by               | Description                                                              |
| :--------------------------------------------------------------- | :----------------------- | :----------------------------------------------------------------------- |
| [`migration_check.sh`](./scripts/migration_check.sh)             | Migration Check          | Alembic upgrade → downgrade → upgrade → `check`; requires `DB_URL`       |
| [`supply_chain_check.sh`](./scripts/supply_chain_check.sh)       | Supply Chain Check       | Poetry metadata, semver check, pip upgrade, pip-audit                    |
| [`check_module_versions.py`](./scripts/check_module_versions.py) | Supply Chain Check       | Validates `[project].version` semver in each `modules/*/pyproject.toml`  |
| [`strata_check.sh`](./scripts/strata_check.sh)                   | Strata Check, pre-commit | Layout, budgets, frontmatter, strict pairing                             |
| [`pre_commit_strata.sh`](./scripts/pre_commit_strata.sh)         | pre-commit               | Sets `STRATA_STRICT_MODULES=1`, `STRATA_DIFF_SOURCE=staged`; skips in CI |
| [`mcp_config_check.sh`](./scripts/mcp_config_check.sh)           | pre-commit               | MCP JSON structure + token scan                                          |
| [`pre_commit_mcp.sh`](./scripts/pre_commit_mcp.sh)               | pre-commit               | CI skip wrapper for MCP check                                            |
| [`update_todos.py`](./scripts/update_todos.py)                   | Auto Updates             | CHANGELOG from GitHub API                                                |
| [`changelog_template.jinja`](./scripts/changelog_template.jinja) | update_todos.py          | CHANGELOG section template                                               |
| [`issue_template.jinja`](./scripts/issue_template.jinja)         | update_todos.py          | Per-issue CHANGELOG entry template                                       |

Shared shell helpers: [`deploy/utils.sh`](../deploy/utils.sh) (`log`, `run_command`).

---

## PR checklist

Before opening or marking a PR ready:

```bash
pre-commit run --all-files
/bin/bash ./deploy/test.sh
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
- Pair `modules/**` / `deploy/**` edits with `.strata/` (or adapter) updates
- Keep PR scope focused

Full agent-oriented checklist: [`AGENTS.md` — PR checklist](../AGENTS.md#pr-checklist).

---

## Troubleshooting

### Strata Check / `strata-validate` failed: code without memory update

```
code paths changed but .strata/ (or AGENTS.md/CLAUDE.md) was not updated
```

Run `/strata:save`, stage `.strata/`, `AGENTS.md`, and/or `CLAUDE.md`, recommit.

### Strata Check did not run on my PR

The workflow path filter excludes `.strata/**`. It runs when `modules/**`, `deploy/**`, or root `pyproject.toml` change. For memory-only edits, rely on local pre-commit or run `strata_check.sh` manually before pushing.

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

| Workflow            | Cron        | Local time hint (US Eastern, DST) |
| :------------------ | :---------- | :-------------------------------- |
| Secret Scan         | `0 5 * * 1` | ~01:00 EDT                        |
| CodeQL Analysis     | `0 6 * * 1` | ~02:00 EDT                        |
| Trivy Security Scan | `0 7 * * 1` | ~03:00 EDT                        |
| Supply Chain Check  | `0 8 * * 1` | ~04:00 EDT                        |

Each workflow also supports **`workflow_dispatch`** from the Actions tab.

---

## Security tab integration

| Source                          | Location                        | Format                            |
| :------------------------------ | :------------------------------ | :-------------------------------- |
| CodeQL                          | Security → Code scanning alerts | Native CodeQL                     |
| Trivy                           | Security → Code scanning alerts | SARIF (`trivy-filesystem`)        |
| Gitleaks                        | Workflow job logs               | Inline findings                   |
| pip-audit                       | Supply Chain Check logs         | Text report with CVE descriptions |
| pre-commit `detect-private-key` | Local / Quality Control logs    | Blocks commit/CI                  |

---

## Environment variables

| Variable                  | Used by                         |           Required           | Example                                                          |
| :------------------------ | :------------------------------ | :--------------------------: | :--------------------------------------------------------------- |
| `DB_URL`                  | `migration_check.sh`            |    Yes (migration checks)    | `postgresql+psycopg2://papita:papita@localhost:5432/papita_test` |
| `STRATA_STRICT_MODULES`   | `strata_check.sh`               |       No (default `0`)       | `1` enables code/memory pairing                                  |
| `STRATA_DIFF_SOURCE`      | `strata_check.sh`               |     No (default `range`)     | `staged` for pre-commit                                          |
| `STRATA_BASE_REF`         | `strata_check.sh` (CI)          |  No (default `origin/main`)  | `origin/main`                                                    |
| `CI` / `GITHUB_ACTIONS`   | pre-commit wrappers             |          Set by GHA          | Skips local-only hooks                                           |
| `SKIP`                    | quality-control pre-commit step |       Set by workflow        | `strata-validate,mcp-config-validate`                            |
| `GITHUB_TOKEN`            | Gitleaks, Auto Updates          |       Provided by GHA        | —                                                                |
| `REPO_OWNER`, `REPO_NAME` | `update_todos.py`               | Set by Auto Updates workflow | —                                                                |

---

## Toolchain pins

| Component                 | Pin                                               |
| :------------------------ | :------------------------------------------------ |
| Python                    | 3.12                                              |
| Poetry                    | 2.1.3 (`snok/install-poetry@v1`)                  |
| PostgreSQL (migration CI) | `postgres:15-alpine`                              |
| checkout                  | `actions/checkout@v5`                             |
| setup-python              | `actions/setup-python@v5`                         |
| pre-commit action         | `pre-commit/action@v3.0.0`                        |
| Codecov                   | `codecov/codecov-action@v4`                       |
| Gitleaks                  | `gitleaks/gitleaks-action@e0c47f4…` (v3)          |
| CodeQL                    | `github/codeql-action@411c4c9…` (v3 init/analyze) |
| Trivy                     | `aquasecurity/trivy-action@a9c7b0f…` (v0.36.0)    |
| SARIF upload              | `github/codeql-action/upload-sarif@54f647b…` (v4) |

Action SHAs are pinned in workflow files for supply-chain reproducibility. Bump deliberately and re-run all affected workflows.
