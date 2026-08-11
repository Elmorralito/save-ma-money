# papita-ingestor-email

Email / Gmail source plugin for Papita ingestion (`papita_ingestor_email`).

|                 |                                                                                                          |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Distribution    | `papita-ingestor-email`                                                                                  |
| Import root     | `papita_ingestor_email`                                                                                  |
| Python          | **≥3.12** (CI/dev). Packaging bounds `requires-python = ">=3.10,<3.15"` match model/api / ingestor-core. |
| Path dependency | `papita-ingestor-core` → `../../ingestor-core`                                                           |
| Epic            | PPT-076 / [#170](https://github.com/Elmorralito/save-ma-money/issues/170)                                |
| Scaffold        | PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)                                |

## Role

Plugin package under `modules/ingestors/`. Implements (in later children) Gmail
fetch + bank-specific parsers. This scaffold is importable smoke only — **no
OAuth, no parsers, no Prefect**.

## Dependency graph (one-way)

```text
papita-ingestor-email  →  papita-ingestor-core  →  papita-transactions-model
```

`papita_txnsapi` / `@papita/web` **must not** import this package.

## Local commands

```bash
make ingestor-install
make ingestor-test
make ingestor-lint
```

## Secrets

See [`.env.example`](.env.example). Real OAuth tokens never belong in git.
