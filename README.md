# save-ma-money

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![interrogate score](./docs/interrogate_badge.svg)
[![coverage score](./docs/coverage-badge.svg)](https://codecov.io/upload/v4?package=github-action-3.1.6-uploader-0.8.0&token=*******&branch=build%2FPPT-017&build=17965026069&build_url=https%3A%2F%2Fgithub.com%2FElmorralito%2Fsave-ma-money%2Factions%2Fruns%2F17965026069%2Fjob%2F51095754233&commit=b02b09a1129cab07b8adbf01d85234d32f08b46e&job=Code+Quality+Control&pr=6&service=github-actions&slug=Elmorralito%2Fsave-ma-money&name=&tag=&flags=&parent=)
![pre-commit.ci status](https://results.pre-commit.ci/badge/github/pre-commit/pre-commit/main.svg)
![flake8 score](./docs/flake8-badge.svg)
[<img src="./docs/share1.png" width="23" style="border-radius: 50%; border: 1px solid #e1e4e8;" alt="Donated to the PSF."/>](https://www.python.org/psf/donations/)
[<img src="./docs/share2.png" width="23" style="border-radius: 50%; border: 1px solid #e1e4e8;" alt="Donated to the PSF."/>](https://www.python.org/psf/donations/)

I'm just trying to **save-ma-money** (also _save-ma-finances_) from my own **ignorance**. This project is a Python monorepo for personal and (hopefully in the future) professional financial data: type-safe PostgreSQL persistence, Alembic migrations, and a FastAPI REST surface. The goal is auditable, tenant-isolated finance data with a tested model layer and a shippable API.

| Package              | Path                                          | Role                                                                      |
| :------------------- | :-------------------------------------------- | :------------------------------------------------------------------------ |
| **papita-txnsmodel** | [`modules/model/`](./modules/model/README.md) | SQLModel schemas, repositories, services, handlers, migrations            |
| **papita-txnsapi**   | [`modules/api/`](./modules/api/README.md)     | FastAPI settings, JWT helpers, target REST contract (routers in progress) |

---

## The problem

Most people and small teams track money across many sources at once — checking accounts, credit cards, loans, investments, and real estate — each exporting data in its own format. Bank CSVs use merchant codes; card portals group charges differently; spreadsheets add custom columns; manual entries fill the gaps. The result is a patchwork of files and one-off scripts rather than a single source of truth.

That fragmentation creates predictable failures:

- **Inconsistent semantics** — The same purchase can be labeled, categorized, and dated differently depending on where it was imported. Without a shared schema, “balance” and “category” mean different things in different tools.
- **Silent import errors** — Weak validation lets bad rows land in storage. Problems surface weeks later when totals do not reconcile.
- **No real audit trail** — Hard deletes and overwritten spreadsheets make it hard to answer “what changed, when, and why?” for taxes, disputes, or compliance.
- **Weak multi-user isolation** — Household or small-business finance needs per-user boundaries. Global lookup tables and shared IDs leak data across tenants when tenancy is bolted on late.
- **Expensive change** — When business rules live in notebooks and ETL scripts, every schema tweak or new account type (banking vs. credit card vs. real estate) duplicates logic instead of extending one domain model.

## The solution

save-ma-money treats finance as **structured domain data**, not ad hoc files. A single PostgreSQL database (`papita_transactions` schema) holds accounts, categories, transactions, and user-scoped extensions under explicit SQLModel tables. Pydantic DTOs validate every read and write; repositories enforce soft delete and conflict-aware upserts; services own transfers, balances, and reports so the same rules apply whether data arrives via bulk ingest or HTTP.

The architecture separates **how data is stored** from **how it is exposed**:

- **`papita-txnsmodel`** — The system of record: migrations, handlers for ingestion, and business logic API routers will call — not reimplement.
- **`papita-txnsapi`** — A thin FastAPI layer: request/response schemas, auth, and routing over existing services.

That split keeps ingestion pipelines and REST endpoints aligned on one tested model, makes balances and reports derivable from the same ledger, and lets the API ship incrementally without forking financial rules into duplicate code paths.

```mermaid
flowchart TB
  subgraph clients [Clients]
    HTTP[HTTP / SDK]
    ETL[Ingestion handlers]
  end

  subgraph api [papita-txnsapi]
    R[Routers]
    S[API schemas]
  end

  subgraph model [papita-txnsmodel]
    SV[Services]
    RP[Repositories]
    DTO[DTOs]
    SM[SQLModel tables]
  end

  DB[(PostgreSQL)]

  HTTP --> R --> S --> SV
  ETL --> SV
  SV --> RP --> DTO --> SM --> DB
```

| Layer   | Location                     | Responsibility                                              |
| :------ | :--------------------------- | :---------------------------------------------------------- |
| Model   | `papita_txnsmodel/model/`    | Tables, relationships, soft delete (`active`, `deleted_at`) |
| Access  | `papita_txnsmodel/access/`   | DTO validation, repository CRUD, pandas DataFrames          |
| Service | `papita_txnsmodel/services/` | Business rules, transfers, reports, account extensions      |
| Handler | `papita_txnsmodel/handlers/` | Load/dump pipelines for bulk ingest                         |
| API     | `papita_txnsapi/`            | Settings, auth helpers, future FastAPI routers              |

**Platform:** PostgreSQL only — Docker Postgres locally (B0), Supabase for hosted environments (B1). DuckDB is deprecated ([#31](https://github.com/Elmorralito/save-ma-money/issues/31)).

---

## Current status and roadmap

| Area                          | Status                                                                                                                                                                                                                              |
| :---------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v3 schema & migrations**    | Written and seeded ([#32](https://github.com/Elmorralito/save-ma-money/issues/32), [#34](https://github.com/Elmorralito/save-ma-money/issues/34)); v3 freeze awaiting maintainer sign-off (G1)                                      |
| **Model layer**               | Production-ready core: accounts, categories, transactions, users, materialized balance views; **351** unit/integration tests in `modules/model/tests`                                                                               |
| **Model hardening (PPT-041)** | [#51](https://github.com/Elmorralito/save-ma-money/issues/51) — service gaps for API readiness (transfers, reports, tenancy guards)                                                                                                 |
| **API**                       | Scaffold only: `Settings`, `AuthSecurityManager`, logging — no `main.py` or routers yet                                                                                                                                             |
| **API epic (PPT-032)**        | [#42](https://github.com/Elmorralito/save-ma-money/issues/42) — FastAPI MVP (32 endpoints) blocked on [#34](https://github.com/Elmorralito/save-ma-money/issues/34) + [#51](https://github.com/Elmorralito/save-ma-money/issues/51) |
| **Design program (PPT-031)**  | [#28](https://github.com/Elmorralito/save-ma-money/issues/28) — schema simplification, API mapping, auth contract, migration runbook                                                                                                |

Post-MVP items (budgets, splits, recurrence) are documented in [`docs/design/PPT-031-v4-extensions.md`](./docs/design/PPT-031-v4-extensions.md) and intentionally out of the v3 MVP scope.

---

## Repository map

```
save-ma-money/
├── pyproject.toml              # workspace root (package-mode = false)
├── modules/
│   ├── model/                  # papita-txnsmodel — primary implementation
│   │   ├── src/papita_txnsmodel/
│   │   ├── alembic/            # migrations
│   │   └── tests/
│   └── api/                    # papita-txnsapi — scaffold stage
│       └── src/papita_txnsapi/
├── deploy/                     # alembic.sh, test.sh, utils.sh
├── docker/database/            # local Postgres 15 Compose
├── docs/design/ · docs/issues/ # PPT-031 design program and briefs
├── .strata/                    # agent memory (hot/warm/cold tiers)
└── .github/workflows/          # CI (quality, security, migrations, strata)
```

---

## Quick start

### 1. Environment

Copy [`.env.example`](./.env.example) and populate the paths below. **Always set `DATABASE_URL`** — omitting it can trigger legacy DuckDB fallback paths.

```bash
cp .env.example modules/api/src/.env
# Edit JWT_SECRET_KEY and DATABASE_URL (PostgreSQL URL required)

# modules/api/src/.env
JWT_SECRET_KEY="change-me"
DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/papita_transactions"
```

For local PostgreSQL, use [`docker/database/docker-compose.yml`](./docker/database/docker-compose.yml) and optional `docker/database/.env`.

### 2. Install dependencies

```bash
# Recommended: Python ~3.12, Poetry 2.1.x
command -v poetry >/dev/null || python -m pip install poetry
make dev
# or
poetry lock && poetry install
```

### 3. Migrate and test

```bash
# PostgreSQL (Docker)
/bin/bash ./deploy/alembic.sh upgrade --docker-local --docker-rm

# Unit and integration tests (model package)
poetry run pytest
# or
/bin/bash ./deploy/test.sh
```

API route tests will be added with the [#42](https://github.com/Elmorralito/save-ma-money/issues/42) epic. See [`modules/api/README.md`](./modules/api/README.md) for package setup details.

---

## Documentation hub

| Document                                                                                 | Scope                                       |
| :--------------------------------------------------------------------------------------- | :------------------------------------------ |
| [Root README](./README.md)                                                               | Monorepo overview (this file)               |
| [`modules/model/README.md`](./modules/model/README.md)                                   | Data model layers, migrations, testing      |
| [`modules/api/README.md`](./modules/api/README.md)                                       | API package status and doc index            |
| [`docs/design/README.md`](./docs/design/README.md)                                       | PPT-031 design program registry and gates   |
| [`docs/issues/`](./docs/issues/README.md)                                                | Issue-linked requirement briefs             |
| [`docs/design/PPT-031-api-model-mapping.md`](./docs/design/PPT-031-api-model-mapping.md) | Endpoint → Service → DTO → SQLModel mapping |
| [`modules/api/API_Endpoints.md.md`](./modules/api/API_Endpoints.md.md)                   | Canonical REST contract (32 MVP endpoints)  |
| [`docs/design/PPT-031-auth-contract.md`](./docs/design/PPT-031-auth-contract.md)         | Local JWT + users auth strategy             |
| [`.github/CI.md`](./.github/CI.md)                                                       | CI workflows, pre-commit, PR checklist      |
| [`AGENTS.md`](./AGENTS.md)                                                               | Agent and contributor operational guide     |
| [CHANGELOG.md](./CHANGELOG.md)                                                           | Issue tracker and merged PR summaries       |

---

## Continuous integration

GitHub Actions workflows, supporting scripts, local pre-commit hooks, scheduled security scans, and the PR checklist are documented in [`.github/CI.md`](./.github/CI.md).

## Changelog

Open issues, completed work, and closing pull-request summaries are maintained in [CHANGELOG.md](./CHANGELOG.md). That file is updated automatically when issues are opened or closed on the default branch.