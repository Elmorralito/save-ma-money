# Papita Transactions Data Model

Welcome to the **backbone of financial data integrity** for the **save-ma-money** monorepo. The importable package is **`papita_txnsmodel`** (PyPI: [`papita-transactions-model`](https://pypi.org/project/papita-transactions-model/)). It is the **system of record**: SQLModel schemas, Alembic migrations, repositories, services, and ingestion handlers. The sibling [`papita-txnsapi`](../api/README.md) exposes HTTP routes that call these services — business rules live here, not in FastAPI routers.

|                     |                                                                                                |
| :------------------ | :--------------------------------------------------------------------------------------------- |
| **PyPI**            | [`papita-transactions-model`](https://pypi.org/project/papita-transactions-model/)             |
| **Import**          | `import papita_txnsmodel`                                                                      |
| **Current version** | See [`pyproject.toml`](./pyproject.toml) / [`CHANGELOG.md`](./CHANGELOG.md) (package releases) |
| **Python**          | `>=3.10,<3.15`                                                                                 |
| **Issue**           | [PPT-024 / #11](https://github.com/Elmorralito/save-ma-money/issues/11)                        |

**Contents:** [Overview](#overview) · [From v0 to v3](#from-v0-to-v3) · [Tenancy](#tenancy-and-security) · [Layers](#architectural-layers) · [Balance reports](#balance-reports-and-materialized-views) · [Database](#database-integration) · [Usage](#usage-examples) · [Install](#install) · [Layout](#package-layout) · [Migrations](#database-migrations) · [Testing](#testing) · [Related docs](#related-documentation)

![PostgreSQL ER diagram — papita_transactions v3 core + balance read models](../../docs/postgres_papita_transactions_v4.png)

Entity-relationship diagram for schema `papita_transactions`: **v3 core tables** (users, accounts, categories, transaction templates, transactions, account extensions, financing) plus **materialized balance views** (`account_balances`, `owner_*_balances`). DDL authority: [`docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../../docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32). Post-MVP additive tables (budgets, splits, recurrence, reconciliation): [`docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a).

## Overview

Personal and small-business finance rarely starts in one clean database. Data arrives as bank CSVs, card portal exports, broker statements, spreadsheets, and manual corrections — each with its own column names, sign conventions, and category vocabulary. Without a shared domain layer, every import script re-implements validation, tenancy, and balance logic differently, and an API built on top inherits those inconsistencies.

`papita_txnsmodel` solves that by treating finance as **structured, tenant-scoped domain data** in PostgreSQL (schema `papita_transactions`). Every path — bulk CSV ingest via handlers, direct service calls in notebooks, or REST endpoints in `papita-txnsapi` — flows through the same DTO validation, repository upserts, and service rules.

### The problem space

- **Data fragmentation** — the same merchant appears as `AMZN MKTP`, `Amazon.com`, or a custom spreadsheet label; categories and dates drift between sources
- **Silent import failures** — weak validation lets malformed rows persist until month-end reconciliation
- **Tenancy risk** — household or multi-user finance requires hard boundaries; global lookup tables and shared deterministic IDs can leak or collide across users
- **Schema complexity** — the legacy v0 model used an `accounts_indexer` hub with eight nullable foreign keys to subtype tables; routing logic lived in Python instead of the database
- **Spec drift** — API documents described `balance`, `category_type`, and `/movements/*` fields that did not exist on SQLModel tables

### Our solution

1. **v3 consolidated schema (PPT-031)** — accounts carry an `account_kind` discriminator; at most one 1:1 extension row; categories replace v0 `types`; transfers are `transaction_kind = TRANSFER` (no separate movements table)
2. **Strict type safety** — Pydantic v2 DTOs at the access layer; SQLModel + PostgreSQL CHECK constraints at persistence
3. **PostgreSQL only** — Docker Postgres locally (B0); Supabase pooler for hosted (B1). **DuckDB is deprecated** — see [platform decision](../../docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31)
4. **Conflict-aware ingestion** — idempotent bulk loads via `PostgreSQLUpserter` and tolerance-aware `upsert_records`
5. **API-ready services (PPT-041)** — account extension orchestration, transfer helpers, FR-12 report aggregations, materialized balance views, live-DB tenancy tests

### Core philosophy

- **Explicit over implicit** — relationships, enums, and denormalizations are documented in design specs and migrations, not inferred at runtime
- **Built-in traceability** — soft delete via `active` and `deleted_at` on `BaseSQLModel`; repositories default to soft delete
- **Single domain layer** — services own invariants; API schemas map to DTOs without duplicating validators
- **Layered architecture** — Model → Access → Service → Handler; see [`.strata/docs/ARCHITECTURE.md`](../../.strata/docs/ARCHITECTURE.md) for the repo codemap

## From v0 to v3

PPT-031 ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)) redesigned the model for **Third Normal Form**, API alignment, and PostgreSQL-only operation. The v3 baseline ships as Alembic revision `a75354933e79` (see [migration runbook](../../docs/design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34)).

| v0 pattern                                         | v3 replacement                                     | Why it changed                                  |
| :------------------------------------------------- | :------------------------------------------------- | :---------------------------------------------- |
| `accounts` + `accounts_indexer` + 6 subtype tables | `accounts` + optional 1:1 `*_account_details`      | Eliminate 8-FK sparse matrix (FR-03)            |
| `types` (ASSETS / LIABILITIES / TRANSACTIONS)      | `categories` with `category_kind` INCOME / EXPENSE | API `/categories/*` vocabulary (FR-13)          |
| `identified_transactions`                          | `transaction_templates`                            | Clear template vs posted split (FR-05)          |
| Single-sided transactions only                     | `transaction_kind` INCOME / EXPENSE / TRANSFER     | `/movements/*` maps to TRANSFER rows (NF-01)    |
| Phantom `balance` column on accounts               | `account_balances` materialized view               | Read model without denormalizing writes (FR-12) |
| DuckDB + PostgreSQL dual dialect                   | PostgreSQL only                                    | Platform decision B0/B1                         |

**Design authority:** [`docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../../docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32) · **as-is audit:** [`docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../../docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)

### Entity relationship (v3)

```
users
  └── owner_id on hot tables (accounts, categories, transactions, transaction_templates, account_financing)

accounts (account_kind, ledger_side, currency, initial_value, current_value)
  ├── banking_account_details      (CHECKING, SAVINGS, CASH)
  ├── trading_account_details      (INVESTMENT_BROKERAGE)
  ├── real_estate_account_details  (REAL_ESTATE)
  ├── credit_card_account_details  (CREDIT_CARD)
  └── loan_account_details         (LOAN_MORTGAGE)

account_financing  ── links asset accounts to loan accounts (financing_share)

categories (parent_id, category_kind)  ── hierarchical income/expense taxonomy

transaction_templates  ── planned / recurring setups
transactions           ── posted ledger (monthly partitions on transaction_ts)
                         INCOME | EXPENSE | TRANSFER + optional template_id

account_balances, owner_yearly_balances, owner_*_balances  ── materialized views
```

### Account kinds

| `account_kind`         | `ledger_side` | Extension table               | Typical use             |
| :--------------------- | :------------ | :---------------------------- | :---------------------- |
| `CHECKING`             | ASSET         | `banking_account_details`     | Day-to-day bank account |
| `SAVINGS`              | ASSET         | `banking_account_details`     | Savings account         |
| `CASH`                 | ASSET         | `banking_account_details`     | Petty cash              |
| `INVESTMENT_BROKERAGE` | ASSET         | `trading_account_details`     | Brokerage / trading     |
| `REAL_ESTATE`          | ASSET         | `real_estate_account_details` | Property                |
| `CREDIT_CARD`          | LIABILITY     | `credit_card_account_details` | Revolving credit        |
| `LOAN_MORTGAGE`        | LIABILITY     | `loan_account_details`        | Mortgage / term loan    |
| `OTHER_ASSET`          | ASSET         | —                             | Generic asset shell     |
| `OTHER_LIABILITY`      | LIABILITY     | —                             | Generic liability shell |

Extension routing for create/update: `services/account_extension_routing.py` → `AccountsService.create_account` / `update_account`.

### Transaction kinds

| `transaction_kind` | Account FKs                                | API surface                              |
| :----------------- | :----------------------------------------- | :--------------------------------------- |
| `INCOME`           | `to_account_id` required                   | `/transactions` POST                     |
| `EXPENSE`          | `from_account_id` required                 | `/transactions` POST                     |
| `TRANSFER`         | both `from_account_id` and `to_account_id` | `/transactions` and `/movements/*` alias |

Templates (`transaction_templates`) hold planned name, amount, and schedule; posted rows in `transactions` may reference `template_id` when matched from recurrence.

## Tenancy and security

**Strategy B (denormalized `owner_id`)** on hot tables — fast tenant-filtered scans without joining through `accounts` on every ledger query. Extension detail tables derive tenancy via `account_id → accounts.owner_id` and do not carry their own `owner_id`.

| Rule                                      | Enforcement                                                                                                                                   |
| :---------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| All owned writes require `owner=UsersDTO` | `BaseService._ensure_owner`; `OwnedTableRepository`                                                                                           |
| Cross-tenant ID access                    | Repository filters return empty / upsert denied                                                                                               |
| Global categories (`owner_id IS NULL`)    | Readable by all tenants; **writes blocked** in `CategoriesService`                                                                            |
| Category identity (FR-15)                 | Composite unique `(owner_id, name, category_kind)` with `NULLS NOT DISTINCT`                                                                  |
| Auth (Track E)                            | `UsersService.register` / `verify_credentials`; see [auth contract](../../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e) |

Live-DB tenancy tests: `tests/tests_papita_txnsmodel/integration/test_tenancy_live_db.py` (require `DATABASE_URL` PostgreSQL).

Row-level security (Supabase B3) is **deferred** — documented in the Supabase brief, not implemented in v3.

## Architectural layers

```mermaid
flowchart TB
  subgraph ingest [Ingestion]
    H[handlers/]
  end

  subgraph domain [papita_txnsmodel]
    SV[services/]
    RP[access/*/repository.py]
    DTO[access/*/dto.py]
    SM[model/]
  end

  subgraph read [Read models]
    MV[views/balance_reports/ MVs]
    RPT[ReportService]
  end

  DB[(PostgreSQL papita_transactions)]

  H --> SV
  SV --> RP --> DTO --> SM --> DB
  SV --> MV
  RPT --> SV
  MV --> DB
```

### 1. Model layer (`src/papita_txnsmodel/model/`)

SQLModel tables on **`BaseSQLModel`**: `active`, `deleted_at`, `created_at`, `updated_at`, schema `papita_transactions`.

- Enums in `model/enums.py` — `AccountKind`, `LedgerSide`, `TransactionKind`, `TransactionStatus`, `CategoryKind`
- **Partitioning** — `transactions` uses monthly RANGE partitions (`config/transaction_partitions.py`; ops script `bin/bash/transaction_partitions.sh`)
- **Intentional denormalizations** — e.g. `transactions.owner_id` for hot-path tenant scans; documented in schema §6

### 2. Access layer (`src/papita_txnsmodel/access/`)

| Component                    | Purpose                                         |
| :--------------------------- | :---------------------------------------------- |
| `TableDTO` / `OwnedTableDTO` | Pydantic validation; `from_dao()` / `to_dao()`  |
| `BaseRepository`             | CRUD, soft delete, pandas `get_records`, upsert |
| `OwnedTableRepository`       | Tenant-scoped reads/writes with `owner` context |
| `access/balance_reports/`    | DTOs for YAML-registered balance report MVs     |

Repositories use `@SQLDatabaseConnector.connect` — never open sessions manually in application code.

### 3. Service layer (`src/papita_txnsmodel/services/`)

The **primary API for application code**. Instantiate with optional shared `connector`; pass `owner=UsersDTO` for tenant scope.

#### Core CRUD services

| Service                       | Domain                                                                                                                                |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| `UsersService`                | Users; `register`, `verify_credentials`, `get_owner`                                                                                  |
| `AccountsService`             | Accounts + extension orchestration                                                                                                    |
| `CategoriesService`           | Income/expense categories                                                                                                             |
| `TransactionTemplatesService` | Recurring/planned templates + payment dues (`list_upcoming_dues`, `mark_paid`, `clear_paid`; helpers in `services/dues.py`) — PPT-070 |
| `TransactionsService`         | Posted ledger + transfer helpers                                                                                                      |
| `AccountFinancingService`     | Asset–loan financing links                                                                                                            |
| `*AccountDetailsService`      | Per-kind 1:1 extension CRUD                                                                                                           |

#### API-readiness (PPT-041)

| Method / module                                              | Purpose                                             |
| :----------------------------------------------------------- | :-------------------------------------------------- |
| `AccountsService.create_account`                             | Atomic account + extension upsert by `account_kind` |
| `AccountsService.get_with_extension`                         | Account shell + detail row for API GET              |
| `AccountsService.get_balance`                                | Balance from `account_balances` MV                  |
| `TransactionsService.list_transfers`                         | Filter `transaction_kind = TRANSFER`                |
| `TransactionsService.create_transfer`                        | Two-legged TRANSFER with validation                 |
| `TransactionsService.complete_transfer` / `cancel`           | Status transitions                                  |
| `ReportService.spending` / `cash_flow` / `trends` / `export` | FR-12 MVP report aggregations                       |
| `refresh_balance_materialized_views`                         | Called after transaction create/delete/upsert       |

Endpoint mapping: [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33) (32 MVP routes → these services).

### 4. Handler layer (`src/papita_txnsmodel/handlers/`)

Bulk **load/dump** pipelines for ETL and file ingest. Handlers resolve dependencies (accounts, categories) and delegate to services.

| Handler                            | Labels (examples)                           |
| :--------------------------------- | :------------------------------------------ |
| `UsersTableHandler`                | users                                       |
| `AccountsTableHandler`             | accounts                                    |
| `CategoriesTableHandler`           | categories                                  |
| `TransactionTemplatesTableHandler` | transaction_templates                       |
| `TransactionsHandler`              | transactions                                |
| `*_account_details` handlers       | per extension table                         |
| `AccountFinancingTableHandler`     | account_financing                           |
| `BalanceReportsHandler`            | balance_reports, reports (read-only export) |

Register via `HandlerFactory.load("papita_txnsmodel.handlers")`. Legacy v0 labels (`types`, `identified_transactions`) warn through `handlers/compat.py`.

## Balance reports and materialized views

Balances are **derived**, not stored on `accounts` rows:

| View                                                                              | Purpose                            |
| :-------------------------------------------------------------------------------- | :--------------------------------- |
| `account_balances`                                                                | Per-account ledger balance         |
| `owner_yearly_balances`                                                           | Combined yearly totals by currency |
| `owner_monthly_balances` / `owner_quarterly_balances` / `owner_biannual_balances` | Period rollups                     |

- SQL definitions: `src/papita_txnsmodel/views/balance_reports/`
- Registry: `config/data/balance_report_filters.yaml` (five `report_id`s)
- **Refresh:** event-driven on `TransactionsService.create`, `delete`, and `upsert_records` via `refresh_balance_materialized_views`
- **Reads:** `BalanceReportsService` / `BalanceReportsHandler` for registered report exports

## Database integration

### SQLDatabaseConnector

```python
from papita_txnsmodel.database.connector import SQLDatabaseConnector

# Always pass a dict when using a URL string (avoids legacy DuckDB path detection)
SQLDatabaseConnector.establish(
    connection={"url": "postgresql+psycopg2://user:pass@localhost:5432/papita_transactions"}
)
```

- Singleton engine; `@SQLDatabaseConnector.connect` manages session lifecycle and rollback on errors
- **PostgreSQL only** for new work; DuckDB upsert/connector paths emit deprecation warnings

### Upsert engine

Bulk idempotent loads use `PostgreSQLUpserter` with `OnUpsertConflictDo` (`UPDATE`, `NOTHING`, `RAISE`). Services expose `missing_upsertions_tol` — exceed the threshold during bulk upsert and a `RuntimeError` raises to prevent silent partial failure.

## Usage examples

### Register a user and resolve tenant context

```python
from papita_txnsmodel.services.users import UsersService

users = UsersService()
users.ensure_password_manager()  # Argon2 bootstrap (required before hash)

registered = users.register(username="demo_user", email="demo@example.com", password="SecurePass1!")
owner = users.get_owner(owner_id=registered.id)
```

### Create account with banking extension

```python
from papita_txnsmodel.services.accounts import AccountsService

accounts = AccountsService(owner=owner)

account = accounts.create_account(
    obj={
        "name": "Checking",
        "account_kind": "CHECKING",
        "currency": "USD",
        "initial_value": 1000.0,
    },
    extension={"entity": "Example Bank", "account_number": "****1234"},
)
balance = accounts.get_balance(account.id)
shell, detail = accounts.get_with_extension(account.id)
```

### Record a transfer between accounts

```python
from papita_txnsmodel.services.transactions import TransactionsService

txns = TransactionsService(owner=owner)

transfer = txns.create_transfer(
    obj={
        "value": 250.0,
        "currency": "USD",
        "from_account_id": checking_id,
        "to_account_id": savings_id,
        "description": "Monthly savings",
    }
)
```

### Spending report for a date window

```python
from datetime import datetime, timezone
from papita_txnsmodel.services.reports import ReportService

reports = ReportService()
summary = reports.spending(
    owner=owner,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2026, 6, 30, tzinfo=timezone.utc),
)
reports.close()
```

### Bulk CSV upsert

```python
import pandas as pd
from papita_txnsmodel.services.transactions import TransactionsService

txns = TransactionsService(owner=owner)
txns.upsert_records(
    df=pd.read_csv("bank_export.csv"),
    on_conflict_do="UPDATE",
    missing_upsertions_tol=0.01,
)
```

## Install

**PyPI name:** [`papita-transactions-model`](https://pypi.org/project/papita-transactions-model/) · **Import:** `papita_txnsmodel` · **Requires:** Python `>=3.10,<3.15`

The published wheel is the **importable library**. Alembic migrations stay in this git checkout (`modules/model/alembic/`) and are applied with [`bin/bash/alembic.sh`](../../bin/bash/alembic.sh) (or Docker) from the monorepo — they are not a separate installable console script in the wheel.

### Quick start (PyPI)

```bash
# Latest release from PyPI
pip install papita-transactions-model

# Pin a release (recommended for apps; versions on PyPI / CHANGELOG.md)
pip install "papita-transactions-model==1.0.1"

# Poetry (external project)
poetry add papita-transactions-model
# or compatible range used by papita-transactions-api:
poetry add "papita-transactions-model>=1.0.0,<2.0"
```

Verify the install:

```bash
python -c "import papita_txnsmodel; from papita_txnsmodel import __version__; print(__version__)"
```

Installed wheels resolve `__version__` via `importlib.metadata` for distribution `papita-transactions-model`. Source checkouts fall back to reading this module’s [`pyproject.toml`](./pyproject.toml).

### Install modes

| Mode                     | When to use                              | Command                                                              |
| :----------------------- | :--------------------------------------- | :------------------------------------------------------------------- |
| **PyPI (production)**    | Apps, CI consumers, external projects    | `pip install papita-transactions-model`                              |
| **Pinned PyPI**          | Reproducible deploys                     | `pip install "papita-transactions-model==<version>"`                 |
| **Poetry (external)**    | Poetry-managed apps outside this repo    | `poetry add papita-transactions-model`                               |
| **Monorepo (develop)**   | Contributors working in `save-ma-money`  | From repo root: `poetry install` (path dep in root `pyproject.toml`) |
| **Editable module only** | Local hack on model in isolation         | `pip install -e modules/model` (from repo root)                      |
| **TestPyPI**             | Pre-release smoke against the test index | See [TestPyPI](#testpypi)                                            |

**API module note:** `papita-transactions-api` depends on `papita-transactions-model (>=1.0.0,<2.0)`. Keep that range in sync when cutting model majors.

### TestPyPI

```bash
# Latest uploaded TestPyPI build (may be a PR .dev preview or a stable re-upload)
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  papita-transactions-model

# Pin a PR preview stamped by Publish model (dev): {version}.dev{run_id}
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "papita-transactions-model==1.0.2.dev18472938471"
```

`--extra-index-url` pulls runtime dependencies from real PyPI when they are not mirrored on TestPyPI.

**PR automation:** when a non-draft, same-repo PR changes `modules/model/**` and the other PR workflow checks pass (at least Secret Scan, Branch sync, Code Quality Control), [`publish-model-dev.yml`](../../.github/workflows/publish-model-dev.yml) publishes `{pyproject_version}.dev{run_id}` to TestPyPI. See [CI.md](../../.github/CI.md#publish-model-dev--testpypi).

### After install — database

1. Provide a PostgreSQL URL (`postgresql+psycopg2://…`).
2. From a **clone of this repository**, run migrations (wheel alone does not ship runnable Alembic env wiring for ops):

```bash
./bin/bash/alembic.sh upgrade --docker-local --docker-rm
# or:
./bin/bash/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"
```

3. Establish the connector in application code (see [Database integration](#database-integration)).

Environment templates: [`.env.example`](../../.env.example) · Compose: [`docker/database/docker-compose.yml`](../../docker/database/docker-compose.yml).

### Build / version / publish (PPT-024 + PPT-066)

Packaging and release automation for **this module only** ([#11](https://github.com/Elmorralito/save-ma-money/issues/11)). Git tag prefix convention: [PPT-066 / #131](https://github.com/Elmorralito/save-ma-money/issues/131) — SSOT in [`.github/CI.md` § Release tagging](../../.github/CI.md#release-tagging-ppt-066).

| Concern                                             | Owner                                                                                                                                         |
| :-------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| Version bump + `py-model-v*` tag + GH release notes | [`release-model.yml`](../../.github/workflows/release-model.yml) ([python-semantic-release](https://python-semantic-release.readthedocs.io/)) |
| Package release notes                               | [`modules/model/CHANGELOG.md`](./CHANGELOG.md) **only**                                                                                       |
| Monorepo issue tracker changelog                    | Root [`CHANGELOG.md`](../../CHANGELOG.md) via [`auto-updates.yml`](../../.github/workflows/auto-updates.yml) — **never** written by PSR       |
| sdist / wheel → TestPyPI / PyPI                     | [`publish-model.yml`](../../.github/workflows/publish-model.yml) (OIDC [Trusted Publishers](https://docs.pypi.org/trusted-publishers/))       |

**Commit style for bumps** — Conventional Commits with model scope (or path-filtered changes under `modules/model/`). Title style `feat/PPT-024: …` alone does **not** drive a version bump:

```text
feat(model): add report window helper
fix(model): correct soft-delete filter
```

**Avoid `[skip ci]` in squash-merge bodies** — GitHub skips all `push` workflows for that commit (including `release-model.yml`). Prefer a clean squash title/body, or put skip tokens only on standalone non-release commits.

#### Local build

```bash
# From repository root — model-only sdist + wheel → dist/
./bin/bash/package.sh --mod model
# or: make package-model

# Manual version bump (escape hatch; prefer PSR on main)
./bin/bash/version.sh --mod model --version 1.0.2 --skip-install

# Local smoke
python -m venv /tmp/model-smoke
/tmp/model-smoke/bin/pip install dist/papita_transactions_model-*.whl
/tmp/model-smoke/bin/python -c "import papita_txnsmodel; print(papita_txnsmodel.__version__)"
```

`bin/bash/package.sh` prefers the `poetry` CLI on `PATH` (as in CI via `snok/install-poetry`), with a `python -m poetry` fallback.

#### Release triggers

| Trigger                                                                                        | Result                                                                                                       |
| :--------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| PR (non-draft, same-repo) touching `modules/model/**` after other PR checks pass               | `publish-model-dev.yml` → TestPyPI as `{version}.dev{run_id}` (not committed)                                |
| Push/merge to `main` touching `modules/model/**` (or `workflow_dispatch` on **Release model**) | PSR bumps version, updates `modules/model/CHANGELOG.md`, tags `py-model-v*`, then **`workflow_call` → PyPI** |
| Tag `py-model-vX.Y.Z` (human/PAT; `GITHUB_TOKEN` tags usually do not cascade)                  | `publish-model.yml` → **PyPI** (canonical escape hatch)                                                      |
| Tag `model-vX.Y.Z` (legacy dual-trigger; deprecated)                                           | `publish-model.yml` → **PyPI** — still accepted; do not create new `model-v*` tags                           |
| Actions → **Publish model package** → `target=testpypi`                                        | **TestPyPI** (OIDC, environment `testpypi`)                                                                  |
| Actions → **Publish model package** → `target=pypi` + `confirm_pypi=publish`                   | **PyPI** (OIDC, environment `pypi`) — manual escape hatch                                                    |

**Operator note:** Trusted Publishers are configured on PyPI/TestPyPI for workflow **`publish-model.yml`** (reusable OIDC publisher) and GitHub Environments `pypi` / `testpypi`. The `testpypi` environment must allow PR branch deployments for dev publishes. Do **not** commit API tokens. Stable publishes after merge use `workflow_call` from `release-model.yml` so they do **not** depend on tag-push cascade (see [CI.md](../../.github/CI.md#publish-model-package-ppt-024)). Tag naming: [Release tagging (PPT-066)](../../.github/CI.md#release-tagging-ppt-066).

## Package layout

```
modules/model/
├── pyproject.toml              # Package metadata + [tool.semantic_release]
├── CHANGELOG.md                # Package releases (PSR; not root CHANGELOG.md)
├── alembic/                    # Migrations (alembic.ini at module root)
├── src/papita_txnsmodel/
│   ├── __meta__.py             # Version (importlib.metadata or pyproject)
│   ├── model/                  # SQLModel tables
│   ├── access/                 # DTOs + repositories per domain
│   ├── services/               # Business logic
│   ├── handlers/               # Load/dump pipelines
│   ├── database/               # Connector, upsert helpers
│   ├── views/                  # Balance report MV SQL + index registry
│   └── config/                 # Partition + MV + balance report specs
└── tests/
    ├── tests_papita_txnsmodel/ # Unit tests (mocked DB)
    └── integration/            # Live PostgreSQL tenancy tests
```

## Database migrations

Alembic targets schema `papita_transactions` on PostgreSQL. v3 seed baseline: **`a75354933e79`**.

```bash
# From repository root — Docker Postgres
./bin/bash/alembic.sh upgrade --docker-local --docker-rm

# Explicit URL (local or Supabase session/direct — not transaction pooler)
./bin/bash/alembic.sh upgrade --url "postgresql+psycopg2://user:pass@host:5432/db"
./bin/bash/alembic.sh downgrade --url "..."   # defaults to head^1
```

Environment templates: [`.env.example`](../../.env.example) · Docker Compose: [`docker/database/docker-compose.yml`](../../docker/database/docker-compose.yml).

### CI migration gate

[`.github/workflows/migration-check.yml`](../../.github/workflows/migration-check.yml): `upgrade head` → `downgrade -1` → `upgrade head` → `alembic check` on PostgreSQL 15.

## Testing

**406** tests (collected) — layered coverage across access, database, services, handlers, views, and package metadata.

| Suite            | Location                                                                               | Requirements                                                    |
| :--------------- | :------------------------------------------------------------------------------------- | :-------------------------------------------------------------- |
| Unit (default)   | `tests/tests_papita_txnsmodel/`                                                        | Mocked DB; no `DATABASE_URL` needed                             |
| Integration      | `tests/.../integration/`                                                               | `DATABASE_URL` must be PostgreSQL; live tests skipped otherwise |
| PPT-041 services | `tests/.../services/test_ppt041_services.py`                                           | Account orchestration, transfers, reports, category guards      |
| PPT-072 dues     | `tests/.../services/test_ppt072_dues.py` (+ `integration/test_ppt072_dues_live_db.py`) | Upcoming window, mark-paid → linked txn, cross-tenant (B0)      |
| Package meta     | `tests/.../test_meta.py`                                                               | `__version__` via importlib.metadata / pyproject fallback       |

```bash
# Standard gate (from repo root)
poetry run pytest modules/model/tests
./bin/bash/test.sh

# Live-DB tenancy suite
DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5435/papita" \
  poetry run pytest modules/model/tests/tests_papita_txnsmodel/integration/
```

## Related documentation

| Document                                                                                                                                                             | Description                                                                                                        |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| [`CHANGELOG.md`](./CHANGELOG.md)                                                                                                                                     | **Package** release notes (python-semantic-release)                                                                |
| [PyPI — papita-transactions-model](https://pypi.org/project/papita-transactions-model/)                                                                              | Published distributions                                                                                            |
| [`.github/CI.md` — Publish model](../../.github/CI.md#publish-model-package-ppt-024)                                                                                 | Release + OIDC publish workflows (PPT-024)                                                                         |
| [`.github/CI.md` — Release tagging](../../.github/CI.md#release-tagging-ppt-066)                                                                                     | Language-prefixed tags (`py-model-v*`) — PPT-066 / [#131](https://github.com/Elmorralito/save-ma-money/issues/131) |
| [`docs/design/README.md`](../../docs/design/README.md)                                                                                                               | PPT-031 design program index                                                                                       |
| [`docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32`](../../docs/design/ARCHITECTURE.md#part-ii--target-schema-v1v3-ppt-031-a2a4-32)           | v3 frozen schema, constraints, G1 checklist                                                                        |
| [`docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30`](../../docs/design/ARCHITECTURE.md#part-i--v0-data-model-audit-ppt-031-a1-30)               | v0 inventory, 3NF analysis, NF register                                                                            |
| [`docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33`](../../docs/design/ARCHITECTURE.md#part-iv--api--model-mapping-ppt-031-c-33)                 | Endpoint → Service → DTO (API epic [#42](https://github.com/Elmorralito/save-ma-money/issues/42))                  |
| [`docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e`](../../docs/design/ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)                     | Local JWT + `UsersService` flows                                                                                   |
| [`docs/design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34`](../../docs/design/ARCHITECTURE.md#part-vii--migration-runbook-ppt-031-d-34)                 | B0/B1 validation, rollback, FR-14                                                                                  |
| [`docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31`](../../docs/issues/README.md#part-ii--ppt-031-c-supabase--fastapi-decision-31)             | B0/B1 platform; B2/B3 deferred                                                                                     |
| [`docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a`](../../docs/design/ARCHITECTURE.md#part-iii--post-mvp-v4-extensions-ppt-031-track-a) | Budgets, splits, recurrence (post-MVP)                                                                             |
| [`modules/api/README.md`](../api/README.md)                                                                                                                          | FastAPI REST surface over this model                                                                               |
| [`README.md`](../../README.md)                                                                                                                                       | Monorepo overview and quick start                                                                                  |
| [`CHANGELOG.md`](../../CHANGELOG.md)                                                                                                                                 | Monorepo **issue** tracker (auto-updates; not package releases)                                                    |

Package metadata: [`pyproject.toml`](./pyproject.toml) (`papita-transactions-model`).
