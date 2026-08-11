# papita-ingestor-core

Source-agnostic ingestion contracts and pipeline for Papita
(`papita_ingestor_core`).

|              |                                                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| Distribution | `papita-ingestor-core`                                                                                            |
| Import root  | `papita_ingestor_core`                                                                                            |
| Python       | **≥3.12** (CI/dev; `ingestor-ci` uses 3.12). Packaging bounds `requires-python = ">=3.10,<3.15"` match model/api. |
| Epic         | PPT-076 / [#170](https://github.com/Elmorralito/save-ma-money/issues/170)                                         |
| Scaffold     | PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)                                         |

## Dependency graph (one-way)

```text
modules/ingestors/*  →  papita-ingestor-core  →  papita-transactions-model
```

- Plugins (e.g. `papita-ingestor-email`) depend on **core**.
- Core depends on **`papita_txnsmodel`** for future upsert bridges — domain rules
  stay in the model layer.
- **`papita_txnsapi` / `@papita/web` must not import plugin packages** (or core
  parsers). API may later expose thin status routers that call model services only.

## Local commands

From the monorepo root (after `poetry install --with development`):

```bash
make ingestor-install
make ingestor-test
make ingestor-lint
```

## Coverage

Scaffold ships import smoke tests only. Coverage target **≥80%** on new module
`src/` trees is owned by PPT-084 / [#178](https://github.com/Elmorralito/save-ma-money/issues/178).

## Secrets

See [`.env.example`](.env.example) for **variable names only**. Real values belong
under `environments/<env>/.env` (never commit secrets).

## Out of scope (this package at scaffold)

Gmail OAuth, bank parsers, Prefect flows, and API routers land in later PPT-076
children — not in this scaffold.
