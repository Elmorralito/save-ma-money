# Papita Public Projects: `save-ma-finances`

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![interrogate score](./docs/interrogate_badge.svg)
[![coverage score](./docs/coverage-badge.svg)](https://codecov.io/upload/v4?package=github-action-3.1.6-uploader-0.8.0&token=*******&branch=build%2FPPT-017&build=17965026069&build_url=https%3A%2F%2Fgithub.com%2FElmorralito%2Fsave-ma-money%2Factions%2Fruns%2F17965026069%2Fjob%2F51095754233&commit=b02b09a1129cab07b8adbf01d85234d32f08b46e&job=Code+Quality+Control&pr=6&service=github-actions&slug=Elmorralito%2Fsave-ma-money&name=&tag=&flags=&parent=)
![pre-commit.ci status](https://results.pre-commit.ci/badge/github/pre-commit/pre-commit/main.svg)
![flake8 score](./docs/flake8-badge.svg)
[<img src="./docs/share1.png" width="23" style="border-radius: 50%; border: 1px solid #e1e4e8;" alt="Donated to the PSF."/>](https://www.python.org/psf/donations/)
[<img src="./docs/share2.png" width="23" style="border-radius: 50%; border: 1px solid #e1e4e8;" alt="Donated to the PSF."/>](https://www.python.org/psf/donations/)

## Index

| Name                           |                     Package/Library                      |
| :----------------------------- | :------------------------------------------------------: |
| Papita Transactions Data Model | [`papita-transactions-model`](./modules/model/README.md) |
| Papita Transactions API        |   [`papita-transactions-api`](./modules/api/README.md)   |

Design and issue-tracker docs live under [`docs/design/`](./docs/design/README.md) and [`docs/issues/`](./docs/issues/README.md).

| README                                                 | Scope                             |
| :----------------------------------------------------- | :-------------------------------- |
| [Root](./README.md)                                    | Monorepo setup, CI, changelog     |
| [`modules/model/README.md`](./modules/model/README.md) | Data model, migrations, tests     |
| [`modules/api/README.md`](./modules/api/README.md)     | API package status and docs index |
| [`docs/design/README.md`](./docs/design/README.md)     | PPT-031 design program registry   |
| [`docs/issues/README.md`](./docs/issues/README.md)     | Issue-linked requirement briefs   |

## Briefing

The `save-ma-finances` ecosystem is a production-grade framework designed to bring high-fidelity integrity to personal and professional financial data. It orchestrates a multi-layered pipeline to transform fragmented financial signals into a clean, auditable data warehouse.

The monorepo currently ships two packages:

- **[Data Model (`papita-txnsmodel`)](./modules/model/README.md)** — Type-safe SQLModel schemas, **PostgreSQL** persistence (DuckDB deprecated — see [PPT-031 platform decision](./docs/issues/PPT-031-C-supabase-decision-brief.md)), Alembic migrations, repositories, services, and ingestion handlers.
- **[API (`papita-txnsapi`)](./modules/api/README.md)** — FastAPI application settings, security helpers, and the target REST surface documented in [`modules/api/API_Endpoints.md.md`](./modules/api/API_Endpoints.md.md) (implementation in progress; see [#25](https://github.com/Elmorralito/save-ma-money/issues/25)).

Planned modules referenced in earlier docs (`registrar`, `plugins`) are not present in this repository yet.

## Development

### Local environment setup

> #### 1. Database environment file
>
> Copy [`.env.example`](./.env.example) and split values into the paths below. **PostgreSQL only** — DuckDB is deprecated ([#31](https://github.com/Elmorralito/save-ma-money/issues/31)).
>
> ```bash
> # Copy template, then populate modules/api/src/.env (required for papita_txnsapi Settings)
> cp .env.example modules/api/src/.env
> # Edit JWT_SECRET_KEY and DATABASE_URL — always set DATABASE_URL (omitting it triggers legacy DuckDB fallback)
>
> # modules/api/src/.env
> JWT_SECRET_KEY="change-me"
> DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/papita_transactions"
>
> # Alembic / Docker Postgres (see docker/database/.env or export directly)
> DB_DRIVER="postgresql+psycopg2"
> DB_HOST="localhost"
> DB_PORT="5432"
> DB_NAME="papita_transactions"
> DB_USER="..."
> DB_PASSWORD="..."
> ```
>
> For local PostgreSQL, see [`docker/database/docker-compose.yml`](./docker/database/docker-compose.yml).

> #### 2. Python / Poetry
>
> ```bash
> # Recommended: Python ~3.12
> command -v poetry >/dev/null || python -m pip install poetry
> make dev
> # or
> poetry lock && poetry install
> ```

### Testing

```bash
# Unit tests (228 tests in modules/model/tests)
poetry run pytest
# or
/bin/bash ./deploy/test.sh
```

API and registrar test directories are configured in `pyproject.toml` but not implemented yet.

### Migrations

```bash
# PostgreSQL (Docker)
/bin/bash ./deploy/alembic.sh upgrade --docker-local --docker-rm

# PostgreSQL (explicit URL)
/bin/bash ./deploy/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"
```

See [`modules/model/README.md`](./modules/model/README.md) for Alembic layout and CI migration gates.

## Continuous integration

| Workflow             | File                                                                                     | Purpose                                                                   |
| :------------------- | :--------------------------------------------------------------------------------------- | :------------------------------------------------------------------------ |
| Code Quality Control | [`.github/workflows/quality-control.yml`](./.github/workflows/quality-control.yml)       | pre-commit, pytest, coverage upload                                       |
| Migration Check      | [`.github/workflows/migration-check.yml`](./.github/workflows/migration-check.yml)       | PostgreSQL upgrade/downgrade + `alembic check`                            |
| Supply Chain Check   | [`.github/workflows/supply-chain-check.yml`](./.github/workflows/supply-chain-check.yml) | `poetry check`, module version metadata, `pip-audit`                      |
| Auto Updates         | [`.github/workflows/auto-updates.yml`](./.github/workflows/auto-updates.yml)             | Regenerates [`CHANGELOG.md`](./CHANGELOG.md) and quality badges on `main` |

Before opening a PR:

```bash
pre-commit run --all-files
poetry run pytest
/bin/bash .github/scripts/supply_chain_check.sh   # poetry check + version metadata
poetry run pip-audit --desc on --skip-editable    # when lockfile / deps change
```

## Changelog

Open issues, completed work, and closing pull-request summaries are maintained in [CHANGELOG.md](./CHANGELOG.md). That file is updated automatically when issues are opened or closed on the default branch.
