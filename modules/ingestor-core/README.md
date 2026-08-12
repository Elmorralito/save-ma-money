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
| Contracts    | PPT-079 / [#173](https://github.com/Elmorralito/save-ma-money/issues/173)                                         |

## Dependency graph (one-way)

```text
modules/ingestors/*  →  papita-ingestor-core  →  papita-transactions-model
```

- Plugins (e.g. `papita-ingestor-email`) depend on **core**.
- Core depends on **`papita_txnsmodel`** for `IngestionBridgeService` — domain rules
  stay in the model layer.
- **`papita_txnsapi` / `@papita/web` must not import plugin packages** (or core
  parsers). API may later expose thin status routers that call model services only.

## What this package owns (PPT-079)

| Surface                                                    | Role                                                                   |
| ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| `RawRecord` / `ParsedRecord` / `FetchFilter` / `RunResult` | Source-agnostic DTOs                                                   |
| `BaseIngestorSource` / `BaseRecordParser`                  | Plugin ABCs                                                            |
| `SourceRegistry` / `ParserRegistry`                        | Decorator registration (+ parser priority)                             |
| `IngestionRunner`                                          | stream fetch → parse → validate → **persist** → **ack**                |
| `to_ingest_transaction_request` / `encode_raw_payload`     | Bridge + DLQ helpers                                                   |
| `BaseIngestorSettings`                                     | `fetch_limit`, `dry_run` (honored by runner; no FK defaults)           |
| `build_base_ingestion_flow()`                              | Optional Prefect factory (`make ingestor-flow-install` / `-E prefect`) |

**Persist** goes only through `IngestionBridgeService.ingest_transaction` /
`record_dead_letter`. Core does not inspect provider-specific payload shapes.

### Runner semantics (locked)

| Path                              | Behavior                                                     |
| --------------------------------- | ------------------------------------------------------------ |
| Persist success                   | Ack at source                                                |
| Parse / validation failure        | Dead-letter, then **ack** (poison-message; stops redelivery) |
| Persist failure / unknown outcome | No ack, no DLQ (retry on next run)                           |
| Ack failure                       | Recorded on `RunResult`; batch continues                     |
| `dry_run=True`                    | Parse/validate only — no persist, DLQ, or ack                |

## Plugin handoff

Downstream issues **consume** these contracts (they do not redefine them):

| Issue                                                                     | Consumes                                     |
| ------------------------------------------------------------------------- | -------------------------------------------- |
| PPT-080 / [#174](https://github.com/Elmorralito/save-ma-money/issues/174) | `BaseIngestorSource` + registry (Gmail)      |
| PPT-081 / [#175](https://github.com/Elmorralito/save-ma-money/issues/175) | `BaseRecordParser` + registry (bank parsers) |
| PPT-082 / [#176](https://github.com/Elmorralito/save-ma-money/issues/176) | `IngestionRunner` + flow factory             |

Register with class attribute `registry_id` (or pass `source_id=` / `parser_id=` to
the decorator). Duplicate registry ids raise. Supply complete FK UUIDs on
`ParsedRecord` before persist — core does not invent account/category defaults.
Pass `owner` as a `UsersDTO` or zero-arg callable into `IngestionRunner`.

**Required:** non-empty `source_ref` on both `RawRecord` and `ParsedRecord` (bridge
idempotency + safe retry). Do not pass `parsers=[]` — omit `parsers` to use the
registry, or pass a non-empty instance list.

## Local commands

From the monorepo root (after `poetry install --with development`):

```bash
make ingestor-install
make ingestor-test
make ingestor-lint
```

Optional Prefect (for `build_base_ingestion_flow` / email flow):

```bash
# Monorepo (root package-mode=false — do not use poetry install -E at root)
make ingestor-flow-install

# Package-local extra still works inside modules/ingestor-core:
# poetry install -E prefect
```

## Coverage

Unit tests cover mapping, registries, runner routing, and an import guard.
Coverage target **≥80%** on new module `src/` trees is owned by PPT-084 /
[#178](https://github.com/Elmorralito/save-ma-money/issues/178).

## Secrets

See [`.env.example`](.env.example) for **variable names only**. Real values belong
under `environments/<env>/.env` (never commit secrets).

## Out of scope

Concrete Gmail / bank parsers, Compose worker packaging, and API routers land in
later PPT-076 children — not in this package.
