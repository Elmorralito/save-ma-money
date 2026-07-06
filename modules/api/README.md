# Papita Transactions API

FastAPI package (`papita-txnsapi`) for the `save-ma-finances` ecosystem. It depends on [`papita-transactions-model`](../model/README.md) for persistence and domain logic.

## Status

Early implementation. The package currently provides:

| Area                   | Location                                |
| :--------------------- | :-------------------------------------- |
| Settings / env loading | `src/papita_txnsapi/config/settings.py` |
| JWT / security helpers | `src/papita_txnsapi/core/security.py`   |
| Logging config         | `src/papita_txnsapi/config/logger.yaml` |

Routers, handlers, and route tests described in the design docs are **not implemented yet** — track progress via [#25](https://github.com/Elmorralito/save-ma-money/issues/25) and the [PPT-031 design program](../../docs/design/README.md).

## Documentation

| Document                                                                       | Description                                                                 |
| :----------------------------------------------------------------------------- | :-------------------------------------------------------------------------- |
| [`API_Endpoints.md.md`](./API_Endpoints.md.md)                                 | Target REST contract (accounts, budgets, transactions, reports, auth)       |
| [`API_Documentation.md.md`](./API_Documentation.md.md)                         | Extended API notes                                                          |
| [`README.md - Project Structure.md`](./README.md%20-%20Project%20Structure.md) | Planned FastAPI layer layout (aspirational; paths differ from current tree) |

## Stack

| Component         | Version / note                                    |
| :---------------- | :------------------------------------------------ |
| FastAPI           | `>=0.135.0,<0.140.0`                              |
| Starlette         | `>=1.3.1,<2.0.0` (pinned for security advisories) |
| Pydantic Settings | `>=2.13.1`                                        |
| Uvicorn           | `>=0.41.0`                                        |
| Data layer        | `papita-transactions-model` (path dependency)     |

## Local setup

From the repository root:

```bash
poetry install
```

Environment variables load from `modules/api/src/.env` (see `Settings.model_config` in `config/settings.py`). `JWT_SECRET_KEY` is required. Database connectivity reuses `papita_txnsmodel.database.connector.SQLDatabaseConnector`.

## Testing

No `modules/api/tests/` suite exists yet. CI runs model unit tests only; API tests will be added with [#25](https://github.com/Elmorralito/save-ma-money/issues/25).

## Related

- Root [README.md](../../README.md) — monorepo setup and CI overview
- [CHANGELOG.md](../../CHANGELOG.md) — issue tracker and merged PR summaries
