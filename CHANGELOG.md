# Changelog

> Auto-generated from GitHub issues by [.github/scripts/update_todos.py](.github/scripts/update_todos.py) via the [Auto Updates](.github/workflows/auto-updates.yml) workflow.

- [ ] [_**[#34](https://github.com/Elmorralito/save-ma-money/issues/34)**_] :: **PPT-031-E: Alembic migration + Supabase PostgreSQL validation** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:38+00:00</sub>_ :weary:

- [ ] [_**[#33](https://github.com/Elmorralito/save-ma-money/issues/33)**_] :: **PPT-031-D: API spec realignment to v3 model** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:36+00:00</sub>_ :weary:

- [ ] [_**[#31](https://github.com/Elmorralito/save-ma-money/issues/31)**_] :: **PPT-031-C: Supabase × FastAPI integration decision record** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:35+00:00</sub>_ :weary:

- [ ] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#28](https://github.com/Elmorralito/save-ma-money/issues/28)**_] :: **refactor/PPT-031: Simplify data model and align API design** :: _<sub style="vertical-align: middle; color: #636363;">2026-03-27 02:03:29+00:00</sub>_ :weary:

- [ ] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#11](https://github.com/Elmorralito/save-ma-money/issues/11)**_] :: **feature/PPT-024: Integrate package and repo versioning** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 21:22:00+00:00</sub>_ :weary:

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#32](https://github.com/Elmorralito/save-ma-money/issues/32)**_] :: **PPT-031-B: Target schema iterations v1–v3 + ER diagram** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:35+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 19:28:43+00:00</sub>_

  > **Closed by** [\_**#37**](https://github.com/Elmorralito/save-ma-money/pull/37): **docs(PPT-031-B): add v1–v3 target schema, v4 extensions, and ER diagrams**

  > Deliver PPT-031 Track A steps A2–A4 ([#32](https://github.com/Elmorralito/save-ma-money/issues/32)) and post-MVP additive schema design on top of the v0 audit ([#30](https://github.com/Elmorralito/save-ma-money/issues/30)). Before this change, #32 deliverables were marked “pending” in the design index with no frozen target schema, migration outline, or ER artifacts. After this change, v3 is documented for G1 maintainer sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28), and v4 extensions are specified as a separate post-G1 migration wave without reopening the v3 freeze.

  >

  > v3 (G1 scope — design only, no SQLModel/Alembic implementation):

  > - Eliminate accounts_indexer; consolidate accounts with account_kind + 1:1 extension tables

  > - Split types into categories (API /categories) and account-kind enum

  > - Map /movements to transactions with transaction_kind = TRANSFER

  > - Defer budgets from G1 MVP; document tenancy (denormalized owner_id), CHECK constraints, intentional denormalizations, backfill/migration outline (FR-14), and G1 sign-off checklist

  > - Address review findings: migration step order, category hierarchy unique key, financing/transaction backfill paths, opening-balance carry-forward

  >

  > v4 (post-G1 additive — does not modify v3 G1 scope):

  > - Budgets, transaction splits, recurrence (RRULE), credit-card cycle fields

  > - Counterparties, categorization rules, reconciliation, transaction events

  > - Structured attachments, import batch tracking (FR-08)

  > - Supplemental materialized views and optional RLS outline (B3)

  > - Explicit exclusions: double-entry journal, new subtype tables, JSONB metadata blobs, stored balance columns

  >

  > Changes by file:

  > - docs/design/PPT-031-v1-schema.md (added): v1 draft, v2 API-domain review, v3 frozen schema (11 tables + account_balances view), mermaid ER, PostgreSQL DDL migration outline §5, denormalizations §6, G1 checklist §7, #32 comment draft

  > - docs/design/PPT-031-v4-extensions.md (added): v4.1–v4.7 phasing, 12+ additive tables/views, ALTER notes for v3 tables, Alembic outline, API coverage matrix, explicit out-of-scope list

  > - docs/postgres_papita_transactions_v3.svg (added): v3 ER diagram companion to v1-schema §4

  > - docs/postgres_papita_transactions_v4.svg (added): v3 core + v4 extensions ER with exclusions legend

  > - docs/design/README.md (modified): link new artifacts; mark A2–A4 and Track A+/F as Written; update gates G0/G1/G2/G4/G8 and recommended review order

  >

  > Closes design deliverable for #32 (implementation remains blocked on G1 sign-off and #34 migrations).

- [x] [_**[#30](https://github.com/Elmorralito/save-ma-money/issues/30)**_] :: **PPT-031-A: Data model audit and 3NF gap analysis (v0)** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:33+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 14:38:22+00:00</sub>_

  > **Closed by** [\_**#35**](https://github.com/Elmorralito/save-ma-money/pull/35): **docs(PPT-031-A): Data model audit and 3NF gap analysis (v0)**

  > docs(PPT-031): add expert-review findings register to v0 audit

  >

  > Nothing is currently staged; this message covers unstaged changes in

  > docs/design/PPT-031-v0-audit.md only.

  >

  > The v0 audit already documented schema inventory and normalization gaps.

  > This update consolidates net-new discoveries from the five-iteration expert

  > review (finance + data modeling) into a numbered findings register so #30,

  > #32, and #33 can track evidence, severity, and remediation in one place.

  >

  > Before: findings were scattered across §1, §3.14, §4.5, §5.6, and §9 with

  > partial overlap and no stable IDs. Transfer/orphan ingest behavior was

  > summarized without the handler filter citation. Cross-references did not

  > link executive summary rows to detailed write-ups.

  >

  > After: §14 introduces NF-01 through NF-12 with severity, evidence, finance

  > impact, and v3 actions. §3.14 expands ledger gaps (NF-01/NF-02/NF-03) and

  > embeds the TransactionsHandler filter. §1, §9, §10, and §13 cross-link to

  > §14; iteration log notes consolidation at stop criterion.

  >

  > Changes by file:

  > - docs/design/PPT-031-v0-audit.md:

  > - §1: link executive summary key findings to §14 register

  > - §3.14: label transfer/orphan/pair-integrity gaps (NF-01–NF-03);

  >     add handler filter code citation; label sign convention as NF-10

  > - §9: add NF ID cross-refs and Expert review register row

  > - §10: add deliverable row for §14 New findings register

  > - §13: update iteration 5 outcome to reference §14 consolidation

  > - §14 (new): full findings register (NF-01–NF-12) with per-finding

  >     evidence, finance impact, and recommended v3/#33 actions, including

  >     critical AccountsIndexerDTO validator defect (NF-04), missing currency/

  >     balance primitives (NF-05/NF-06), API phantom fields table (NF-09)

  >

  > No production code changes. Documentation only; supports PPT-031 Track A

  > Step A1 (#30) and informs target schema work (#32).

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#25](https://github.com/Elmorralito/save-ma-money/issues/25)**_] :: **feature/PPT-030: API Implementation** :: _<sub style="vertical-align: middle; color: #636363;">2026-01-03 15:55:21+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:22:43+00:00</sub>_

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#24](https://github.com/Elmorralito/save-ma-money/issues/24)**_] :: **feature/PPT-029: Define Data Model for Isolating finances per User** :: _<sub style="vertical-align: middle; color: #636363;">2026-01-03 15:54:11+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:22:42+00:00</sub>_

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#17](https://github.com/Elmorralito/save-ma-money/issues/17)**_] :: **fix/PPT-026: Work in entity Relationships between DuckDB tables.** :: _<sub style="vertical-align: middle; color: #636363;">2025-11-29 20:16:41+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:22:42+00:00</sub>_

- [x] [_**[#26](https://github.com/Elmorralito/save-ma-money/issues/26)**_] :: **feature/PPT-031: Add users to the data model** :: _<sub style="vertical-align: middle; color: #636363;">2026-01-28 00:17:05+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-02-04 23:31:20+00:00</sub>_

  > **Closed by** [\_**#27**](https://github.com/Elmorralito/save-ma-money/pull/27): **Feat/ppt 031**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#5](https://github.com/Elmorralito/save-ma-money/issues/5)**_] :: **feature/PPT-019** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:44:08+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-07 22:44:59+00:00</sub>_

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#7](https://github.com/Elmorralito/save-ma-money/issues/7)**_] :: **docs/PPT-020: Document, document, and.... document...** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 02:40:49+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-02 23:08:02+00:00</sub>_

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#10](https://github.com/Elmorralito/save-ma-money/issues/10)**_] :: **docs/PPT-023: API Documentation** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:41:26+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-02 23:06:15+00:00</sub>_

  > **Closed by** [\_**#23**](https://github.com/Elmorralito/save-ma-money/pull/23): **docs(PPT-023): Finishing documentation. TODO: API documentation, it'l…**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#18](https://github.com/Elmorralito/save-ma-money/issues/18)**_] :: **feat/PPT-027: Update the file system accessors to use smart-open instead.** :: _<sub style="vertical-align: middle; color: #636363;">2025-12-22 22:31:51+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 04:07:55+00:00</sub>_

  > **Closed by** [\_**#22**](https://github.com/Elmorralito/save-ma-money/pull/22): **feat(PPT-027): Introduce CSV file plugin and CLI support**

  > - Added CSVFilePlugin for loading and processing CSV files, integrating with the transaction tracking system.

  > - Implemented CLICSVFilePlugin to provide command-line interface capabilities for CSV file handling.

  > - Enhanced error handling and argument parsing for improved user experience in CLI operations.

  > - Updated versioning for existing Excel file loader plugins to 1.0.1.

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#20](https://github.com/Elmorralito/save-ma-money/issues/20)**_] :: **feat/PPT-028: Add feature to list available plugins** :: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 00:25:15+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 02:42:12+00:00</sub>_

  > **Closed by** [\_**#21**](https://github.com/Elmorralito/save-ma-money/pull/21): **feat(PPT-028): Enhance plugin metadata and CLI utilities**

  > - Introduced author information in the plugin metadata model, allowing for detailed author attribution.

  > - Added a new function to list available plugins, enhancing the CLI with the ability to display plugin details.

  > - Updated the registry discovery method to support discovering disabled plugins and improved module handling.

  > - Enhanced error handling and logging in the CLI for better user feedback when listing plugins.

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#14](https://github.com/Elmorralito/save-ma-money/issues/14)**_] :: **test/PPT-025: Unit test design, implementation and code refinement** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-05 20:07:41+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 01:05:24+00:00</sub>_

  > **Closed by** [\_**#19**](https://github.com/Elmorralito/save-ma-money/pull/19): **test(PPT-025)**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#4](https://github.com/Elmorralito/save-ma-money/issues/4)**_] :: **feature/PPT-018** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:29:57+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-11-29 15:46:35+00:00</sub>_

  > **Closed by** [\_**#16**](https://github.com/Elmorralito/save-ma-money/pull/16): **feat(PPT-018): Registrar**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#8](https://github.com/Elmorralito/save-ma-money/issues/8)**_] :: **docs/PPT-021: Tracker/Loader Documentation** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:39:56+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-10 01:41:35+00:00</sub>_

  > **Closed by** [\_**#15**](https://github.com/Elmorralito/save-ma-money/pull/15): **docs(PPT-021): Defining the design of the tracker/registrar module**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#9](https://github.com/Elmorralito/save-ma-money/issues/9)**_] :: **build/PPT-022: Data model indexer** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:40:47+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-05 20:03:12+00:00</sub>_

  > **Closed by** [\_**#12**](https://github.com/Elmorralito/save-ma-money/pull/12): **build(PPT-022): Data model indexer**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#3](https://github.com/Elmorralito/save-ma-money/issues/3)**_] :: **build/PPT-017** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:19:36+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 02:18:51+00:00</sub>_

  > **Closed by** [\_**#6**](https://github.com/Elmorralito/save-ma-money/pull/6): **build(PPT-017): Creating CI actions**

- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#1](https://github.com/Elmorralito/save-ma-money/issues/1)**_] :: **feature/PPT-016** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-18 23:46:39+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-09-22 22:16:22+00:00</sub>_

  > **Closed by** [\_**#2**](https://github.com/Elmorralito/save-ma-money/pull/2): **feat(PPT-016): Adding data model.**
