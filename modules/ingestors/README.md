# Ingestor plugins

Concrete source plugins for PPT-076 / [#170](https://github.com/Elmorralito/save-ma-money/issues/170).

| Package                 | Path               | Status                                                                               |
| ----------------------- | ------------------ | ------------------------------------------------------------------------------------ |
| `papita-ingestor-email` | [`email/`](email/) | Scaffold (PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)) |
| bank-api (future)       | —                  | Later children                                                                       |

Shared contracts live in [`../ingestor-core`](../ingestor-core) (`papita-ingestor-core`).

**Rule:** plugins → core → model. API and web must not import plugins.
