# Changelog — papita-ingestor-core

Release notes for the **`papita-ingestor-core`** package.

This file is **not** the monorepo issue tracker changelog. Root
[`CHANGELOG.md`](../../CHANGELOG.md) is owned by
[`.github/workflows/auto-updates.yml`](../../.github/workflows/auto-updates.yml).

## 0.0.1 (unreleased)

### Added

- Package scaffold for PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)
  (`src/papita_ingestor_core`, smoke tests, path dependency on
  `papita-transactions-model`).
- Core contracts for PPT-079 / [#173](https://github.com/Elmorralito/save-ma-money/issues/173):
  DTOs, source/parser ABCs + registries, error taxonomy, bridge mapping,
  `IngestionRunner` (persist-then-ack; DLQ-then-ack poison semantics),
  `BaseIngestorSettings` (`fetch_limit` / `dry_run`), optional Prefect flow
  factory (`poetry install -E prefect`).
