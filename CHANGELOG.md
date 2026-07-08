# Changelog

> Auto-generated from GitHub issues by [.github/scripts/update_todos.py](.github/scripts/update_todos.py) via the [Auto Updates](.github/workflows/auto-updates.yml) workflow.


- [ ] [_**[#50](https://github.com/Elmorralito/save-ma-money/issues/50)**_] :: **test/PPT-040: [api] Integration test suite and CI dual-target gate (B0 + B1)** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:55:06+00:00</sub>_ :weary:


- [ ] [_**[#49](https://github.com/Elmorralito/save-ma-money/issues/49)**_] :: **ops/PPT-039: [api] Supabase B1 production wiring and dual-environment validation** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:55:05+00:00</sub>_ :weary:


- [ ] [_**[#48](https://github.com/Elmorralito/save-ma-money/issues/48)**_] :: **feat/PPT-038: [api] Reports read models (spending, cash-flow, trends, export)** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:55:04+00:00</sub>_ :weary:


- [ ] [_**[#47](https://github.com/Elmorralito/save-ma-money/issues/47)**_] :: **feat/PPT-037: [api] Transactions CRUD and movements TRANSFER alias router** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:55:00+00:00</sub>_ :weary:


- [ ] [_**[#46](https://github.com/Elmorralito/save-ma-money/issues/46)**_] :: **feat/PPT-036: [api] Accounts and categories CRUD (v3 model)** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:54:52+00:00</sub>_ :weary:


- [ ] [_**[#45](https://github.com/Elmorralito/save-ma-money/issues/45)**_] :: **feat/PPT-034: [api] FastAPI app scaffold, middleware, and health probes** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:54:50+00:00</sub>_ :weary:


- [ ] [_**[#44](https://github.com/Elmorralito/save-ma-money/issues/44)**_] :: **feat/PPT-035: [api] Auth routes and tenant context module (local JWT)** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:54:49+00:00</sub>_ :weary:


- [ ] [_**[#43](https://github.com/Elmorralito/save-ma-money/issues/43)**_] :: **docs/PPT-033: [api] Validate API spec against v3 model implementation** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:54:48+00:00</sub>_ :weary:


- [ ] [_**[#42](https://github.com/Elmorralito/save-ma-money/issues/42)**_] :: **feat/PPT-032: [EPIC][api] FastAPI MVP on v3 model + Supabase PostgreSQL** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-07 23:54:37+00:00</sub>_ :weary:


- [ ] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#11](https://github.com/Elmorralito/save-ma-money/issues/11)**_] :: **feature/PPT-024: Integrate package and repo versioning** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 21:22:00+00:00</sub>_ :weary:


- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#52](https://github.com/Elmorralito/save-ma-money/issues/52)**_] :: **ops/PPT-042: [infra] CI adoption badge GitHub Action** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 01:30:57+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 20:36:13+00:00</sub>_

  > **Closed by** [_**#56**](https://github.com/Elmorralito/save-ma-money/pull/56): **ci(badge): add CI adoption scoring workflow and README badge (PPT-042)**
  >

  > Implement ops/PPT-042 (#52): a config-file-based CI maturity evaluator that scores repository adoption signals, maintains a dynamic shields.io badge in README.md, and gives developers optional local pre-push feedback. Before this change, CI maturity was documented only in .github/CI.md with no automated visibility in the README or repeatable rubric.

  > 

  > After this change, a GitHub Actions workflow evaluates CI on push/PR to main, weekly schedule, and workflow_dispatch; commits badge updates with [skip ci] to avoid loops; and exposes level/score/tools in the job summary. Local developers can optionally install a pre-push hook for advisory output that never blocks push.

  > 

  > Changes by file:

  > - .github/workflows/ci-badge.yml: new workflow using Python 3.12, evaluate_ci.py, README update, git-auto-commit-action@v5, and step summary; skips push runs when head commit contains [skip ci]

  > - .github/scripts/evaluate_ci.py: scoring engine detecting 10 CI platforms, quality signals (pre-commit, security workflows, coverage, Docker, deploy, Strata, linting, Dependabot), keyword bonuses in workflow YAML, capped 100-point rubric with Advanced/Intermediate/Basic/None levels; writes badge_url, badge_link, level, score, tools, and quality_signals to GITHUB_OUTPUT; supports --update-readme for README badge replacement

  > - .github/scripts/pre_commit_ci_adoption.sh: local pre-push wrapper that skips in CI, infers REPO_NAME from origin, runs evaluate_ci.py, and always exits 0 (advisory only)

  > - .pre-commit-config.yaml: register ci-adoption-check hook at pre-push stage (local-only; not invoked by CI pre-commit)

  > - README.md: add CI Adoption shields.io badge linking to GitHub Actions (current measured level: Intermediate, score 65)

  > - .github/CI.md: document workflow, scoring rubric, triggers, local usage, pre-push install instructions, hook inventory, supporting scripts table, and scheduled scan entry

  > 

  > Closes PPT-042 / #52.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#28](https://github.com/Elmorralito/save-ma-money/issues/28)**_] :: **refactor/PPT-031: Simplify data model and align API design** :: _<sub style="vertical-align: middle; color: #636363;">2026-03-27 02:03:29+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 18:11:25+00:00</sub>_


- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#51](https://github.com/Elmorralito/save-ma-money/issues/51)**_] :: **perf/PPT-041: [model] Harden v3 data model for API readiness** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 00:27:45+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 18:07:44+00:00</sub>_

  > **Closed by** [_**#54**](https://github.com/Elmorralito/save-ma-money/pull/54): **feat(model): harden v3 services for PPT-041 API readiness**
  >

  > Close model-layer gaps from the PPT-032 coverage audit (G1, G3, G5) so the FastAPI epic can wire routers against a complete service surface. Before this change, AccountsService only exposed base CRUD, TransactionsService refreshed balance MVs only on bulk upsert, ReportService did not exist, tenancy was mock-tested only, and repository upserts could fail for owned tables due to a missing owner context on pre-read. The root README still described a legacy monorepo layout (registrar/plugins, 228 tests, issue #25) and lacked a business/technical overview aligned with PPT-031 and PPT-032.

  > 

  > After this change, the model package exposes account extension orchestration, transfer helpers, FR-12 report aggregations, live-PostgreSQL tenancy tests, and corrected repository upsert/category-query behavior validated on B0 Docker Postgres (351 tests passing). The root README is rewritten as the monorepo entry point: problem/solution narrative, layered architecture diagram, current status (PPT-041 #51, API epic #42), quick start, and documentation hub — with all registrar references removed and PostgreSQL-only platform called out.

  > 

  > Changes by file:

  > - .strata/docs/ARCHITECTURE.md: document PPT-041 API-readiness services, extension routing, MV refresh on all transaction writes, and integration test location (Strata strict-mode pairing)

  > - modules/model/src/papita_txnsmodel/services/account_extension_routing.py (new): map account_kind to extension service/DTO pairs and requires_extension() helper

  > - modules/model/src/papita_txnsmodel/services/accounts.py: add create_account, update_account, get_with_extension, and get_balance; wire AccountBalancesService and extension upserts by kind

  > - modules/model/src/papita_txnsmodel/services/transactions.py: add list_transfers, create_transfer, complete_transfer, cancel; refresh balance MVs on create and delete (not only upsert_records)

  > - modules/model/src/papita_txnsmodel/services/reports.py (new): implement ReportService.spending, cash_flow, trends, and export per mapping §5.8 / FR-12

  > - modules/model/src/papita_txnsmodel/services/categories.py: block tenant writes to global categories (owner_id IS NULL) via _reject_global_category_write and _existing_category_owner_id

  > - modules/model/src/papita_txnsmodel/services/__init__.py: export ReportService, owner balance services, and refresh_balance_materialized_views

  > - modules/model/src/papita_txnsmodel/access/base/repository.py: fix upsert_record to pass dto_type to get_record_by_id, use add when no row exists / merge when found, and forward owner from OwnedTableRepository.upsert_record

  > - modules/model/src/papita_txnsmodel/access/categories/repository.py: use SQLAlchemy .is_(None) so global category rows are readable in live queries

  > - modules/model/tests/tests_papita_txnsmodel/services/test_ppt041_services.py (new): unit tests for account orchestration, transfer helpers, ReportService, and global-category write guard

  > - modules/model/tests/tests_papita_txnsmodel/integration/conftest.py (new): PostgreSQL session fixtures; skip unless DATABASE_URL is PostgreSQL; establish connector via {"url": ...} dict

  > - modules/model/tests/tests_papita_txnsmodel/integration/test_tenancy_live_db.py (new): live-DB cross-tenant upsert denial, read isolation, and global-category read/write rules on B0

  > - modules/model/tests/tests_papita_txnsmodel/integration/__init__.py (new): package marker for integration suite

  > - modules/model/tests/tests_papita_txnsmodel/access/base/test_repository.py: align upsert tests with corrected add-on-insert / merge-on-update semantics

  > - README.md: rewrite root overview — rename title to save-ma-money; expand problem/solution sections (multi-source fragmentation, tenancy, audit trail); add mermaid layer diagram and status table (351 tests, #51/#42/#28); repository map, quick start, and documentation hub; remove registrar/plugins tale #25/228-test references; link to module READMEs and PPT-031 design docs

  > 

  > Unblocks PPT-032 router work (issues #42–#50). No API-layer code changes. Generated artifacts (docs/coverage.xml, docs/interrogate_badge.svg, CHANGELOG.md) are intentionally excluded from this commit.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#34](https://github.com/Elmorralito/save-ma-money/issues/34)**_] :: **PPT-031-E: Alembic migration + Supabase PostgreSQL validation** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:38+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-08 01:51:39+00:00</sub>_

  > **Closed by** [_**#53**](https://github.com/Elmorralito/save-ma-money/pull/53): **feat(model)!: implement PPT-031 v3 schema, balance reports, and trans…**
  >

  > feat(model)!: implement PPT-031 v3 schema, balance reports, and transaction partitioning

  > 

  > Deliver the PPT-031 v3 model refactor on branch refactor/PPT-031e: squash legacy

  > Alembic history into a single seed revision, reshape domain entities around

  > categories and account extensions, add balance-report materialized views with a

  > full access/service/handler stack, and partition transactions by month with

  > 10-year retention. Before this change, the model carried incremental migrations

  > from 2025–2026, separate assets/liabilities/indexers/types domains, and a

  > A single unpartitioned transactions table with no balance-report read models.

  > After this change, fresh databases will be upgraded through a linear v3 chain ending at

  > g4b5c6d7e8f9, expose YAML-driven balance report queries against five MVs,

  > and maintain monthly transaction child tables via run_partition_maintenance().

  > 

  > BREAKING CHANGE: Existing databases cannot be upgraded in place from pre-v3

  > migrations. Five legacy revisions are removed and replaced by

  > a75354933e79 (v3 seed) plus six follow-on revisions. The transactions

  > The table is recreated as a range-partitioned parent with a composite primary key

  > (id, transaction_ts). Domains assets, liabilities, indexers, and

  > types are removed; use categories, account_details, and

  > account_financing instead. Rebuild from scratch or follow

  > docs/design/PPT-031-migration-runbook.md.

  > 

  > Note: eight unstaged files remain outside this commit — pyproject.toml

  > (SQLFluff config), .pre-commit-config.yaml (SQLFluff hooks), .github/

  > workflows/quality-control.yml, and five reformatted views/balance_reports/

  > *.sql files. Stage them before commit or land in a follow-up chore commit.

  > 

  > Migration chain (head: g4b5c6d7e8f9):

  > - a75354933e79 — v3 seed schema (accounts, categories, transactions, users, …)

  > - b8f2c1d04e3a — owner_yearly_balances materialized view

  > - c4a8e2f19b7d — monthly/quarterly/biannual owner period balance MVs

  > - d1e9a4f62c8b — segment account_balances per owner

  > - e2f3a4b5c6d7 — MV fetch-support indexes

  > - f3a4b5c6d7e8 — table query indexes

  > - g4b5c6d7e8f9 — monthly transactions partitioning with reversible downgrade

  > 

  > Changes by area:

  > 

  > **Alembic & deploy**

  > - modules/model/alembic/env.py: register alembic_utils MV entities; add

  >   include_object to ignore monthly partition child tables during autogeneration

  > - modules/model/alembic/versions/2025_10_14_2211-93420bed0a90_seed_version.py:

  >   deleted (superseded by v3 seed)

  > - modules/model/alembic/versions/2026_01_28_1851-53fec3d56681_adding_new_fields.py:

  >   deleted

  > - modules/model/alembic/versions/2026_01_28_1921-06b97dfcb5c7_adding_user_table_and_owner_columns.py:

  >   deleted

  > - modules/model/alembic/versions/2026_01_30_0046-255bb7382571_types_update.py:

  >   deleted

  > - modules/model/alembic/versions/2026_01_30_0334-ccaa69123f7e_fixing_issue_with_user.py:

  >   deleted

  > - modules/model/alembic/versions/2026_07_07_2325-a75354933e79_ppt_031_v3_seed_version.py:

  >   new v3 baseline schema

  > - modules/model/alembic/versions/2026_07_07_1915-b8f2c1d04e3a_add_owner_yearly_balances_materialized_view.py:

  >   new

  > - modules/model/alembic/versions/2026_07_07_1919-c4a8e2f19b7d_add_owner_period_balance_materialized_views.py:

  >   new

  > - modules/model/alembic/versions/2026_07_07_1922-d1e9a4f62c8b_segment_account_balances_per_owner.py:

  >   new

  > - modules/model/alembic/versions/2026_07_07_1946-e2f3a4b5c6d7_add_balance_report_fetch_support_indexes.py:

  >   new

  > - modules/model/alembic/versions/2026_07_07_1954-f3a4b5c6d7e8_add_table_query_indexes.py:

  >   new

  > - modules/model/alembic/versions/2026_07_07_2015-g4b5c6d7e8f9_partition_transactions_monthly.py:

  >   new monthly partition swap

  > - deploy/alembic.sh: refactor for Poetry/venv resolution and Docker-local flows

  > - deploy/transaction_partitions.sh: new CLI wrapper for partition maintenance

  > 

  > **Model layer**

  > - modules/model/src/papita_txnsmodel/model/transactions.py: composite PK

  >   (id, transaction_ts), PostgreSQL range partitioning metadata

  > - modules/model/src/papita_txnsmodel/model/accounts.py: v3 account shape

  > - modules/model/src/papita_txnsmodel/model/account_details.py: new

  > - modules/model/src/papita_txnsmodel/model/account_financing.py: new

  > - modules/model/src/papita_txnsmodel/model/categories.py: new (replaces types)

  > - modules/model/src/papita_txnsmodel/model/users.py: owner-scoped updates

  > - modules/model/src/papita_txnsmodel/model/base.py: __table_args__ typing fix

  > - modules/model/src/papita_txnsmodel/model/enums.py: v3 enum consolidation

  > - modules/model/src/papita_txnsmodel/model/contstants.py: MV/view name constants

  > - modules/model/src/papita_txnsmodel/model/__init__.py: export v3 entities

  > - modules/model/src/papita_txnsmodel/model/assets.py: deleted

  > - modules/model/src/papita_txnsmodel/model/liabilities.py: deleted

  > - modules/model/src/papita_txnsmodel/model/indexers.py: deleted

  > - modules/model/src/papita_txnsmodel/model/types.py: deleted

  > 

  > **Access layer**

  > - modules/model/src/papita_txnsmodel/access/balance_reports/__init__.py: new

  > - modules/model/src/papita_txnsmodel/access/balance_reports/exceptions.py: new

  > - modules/model/src/papita_txnsmodel/access/balance_reports/filter_validation.py:

  >   new YAML filter validation

  > - modules/model/src/papita_txnsmodel/access/balance_reports/query_sql.py: new

  >   shared SQL builder

  > - modules/model/src/papita_txnsmodel/access/balance_reports/repository.py: new

  >   unified balance report repository

  > - modules/model/src/papita_txnsmodel/access/account_balances/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/account_balances/repository.py: new

  > - modules/model/src/papita_txnsmodel/access/account_details/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/account_details/repository.py: new

  > - modules/model/src/papita_txnsmodel/access/account_financing/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/account_financing/repository.py: new

  > - modules/model/src/papita_txnsmodel/access/categories/__init__.py: new

  > - modules/model/src/papita_txnsmodel/access/categories/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/categories/repository.py: new

  > - modules/model/src/papita_txnsmodel/access/owner_period_balances/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/owner_period_balances/repository.py:

  >   new

  > - modules/model/src/papita_txnsmodel/access/owner_yearly_balances/dto.py: new

  > - modules/model/src/papita_txnsmodel/access/owner_yearly_balances/repository.py:

  >   new

  > - modules/model/src/papita_txnsmodel/access/accounts/dto.py: v3 account DTOs

  > - modules/model/src/papita_txnsmodel/access/accounts/repository.py: import fix

  > - modules/model/src/papita_txnsmodel/access/transactions/dto.py: v3 transaction

  >   DTO with partition-aware fields

  > - modules/model/src/papita_txnsmodel/access/transactions/repository.py: v3 query

  >   updates

  > - modules/model/src/papita_txnsmodel/access/base/dto.py: owned-table helpers

  > - modules/model/src/papita_txnsmodel/access/base/repository.py: owner-scoped base

  > - modules/model/src/papita_txnsmodel/access/assets/dto.py: deleted

  > - modules/model/src/papita_txnsmodel/access/assets/repository.py: deleted

  > - modules/model/src/papita_txnsmodel/access/liabilities/dto.py: deleted

  > - modules/model/src/papita_txnsmodel/access/liabilities/repository.py: deleted

  > - modules/model/src/papita_txnsmodel/access/indexers/dto.py: deleted

  > - modules/model/src/papita_txnsmodel/access/indexers/repository.py: deleted

  > - modules/model/src/papita_txnsmodel/access/types/dto.py: deleted

  > - modules/model/src/papita_txnsmodel/access/types/repository.py: deleted

  > 

  > **Services layer**

  > - modules/model/src/papita_txnsmodel/services/balance_reports.py: new

  > - modules/model/src/papita_txnsmodel/services/balance_views.py: new MV refresh

  > - modules/model/src/papita_txnsmodel/services/account_balances.py: new

  > - modules/model/src/papita_txnsmodel/services/account_details.py: new

  > - modules/model/src/papita_txnsmodel/services/account_financing.py: new

  > - modules/model/src/papita_txnsmodel/services/categories.py: new

  > - modules/model/src/papita_txnsmodel/services/owner_period_balances.py: new

  > - modules/model/src/papita_txnsmodel/services/owner_yearly_balances.py: new

  > - modules/model/src/papita_txnsmodel/services/transactions.py: v3 transaction

  >   service updates

  > - modules/model/src/papita_txnsmodel/services/extends.py: refactor for v3 domains

  > - modules/model/src/papita_txnsmodel/services/base.py: base service tweaks

  > - modules/model/src/papita_txnsmodel/services/__init__.py: export v3 services

  > - modules/model/src/papita_txnsmodel/services/assets.py: deleted

  > - modules/model/src/papita_txnsmodel/services/liabilities.py: deleted

  > - modules/model/src/papita_txnsmodel/services/indexers.py: deleted

  > - modules/model/src/papita_txnsmodel/services/types.py: deleted

  > 

  > **Handlers layer**

  > - modules/model/src/papita_txnsmodel/handlers/balance_reports.py: new load/dump

  > - modules/model/src/papita_txnsmodel/handlers/account_extensions.py: new

  > - modules/model/src/papita_txnsmodel/handlers/categories.py: new

  > - modules/model/src/papita_txnsmodel/handlers/users.py: new

  > - modules/model/src/papita_txnsmodel/handlers/matching.py: new reference-index

  >   matching

  > - modules/model/src/papita_txnsmodel/handlers/compat.py: new v2→v3 compat shim

  > - modules/model/src/papita_txnsmodel/handlers/accounts.py: slim down for v3

  > - modules/model/src/papita_txnsmodel/handlers/transactions.py: major v3 refactor

  > - modules/model/src/papita_txnsmodel/handlers/base.py: handler base updates

  > - modules/model/src/papita_txnsmodel/handlers/factory.py: register v3 handlers

  > - modules/model/src/papita_txnsmodel/handlers/helpers.py: helper updates

  > - modules/model/src/papita_txnsmodel/handlers/__init__.py: export v3 handlers

  > - modules/model/src/papita_txnsmodel/handlers/types.py: deleted

  > 

  > **Config package (retire configs/)**

  > - modules/model/src/papita_txnsmodel/config/__init__.py: new lazy exports

  > - modules/model/src/papita_txnsmodel/config/constants.py: path constants

  > - modules/model/src/papita_txnsmodel/config/balance_report_specs.py: YAML registry

  >   loader

  > - modules/model/src/papita_txnsmodel/config/materialized_views.py: MV registry

  > - modules/model/src/papita_txnsmodel/config/transaction_partitions.py: monthly

  >   partition DDL, retention, maintenance

  > - modules/model/src/papita_txnsmodel/config/data/__init__.py: new

  > - modules/model/src/papita_txnsmodel/config/data/balance_report_filters.yaml: new

  >   filter definitions

  > - modules/model/src/papita_txnsmodel/config/data/logger.yaml: moved from configs/.

  > - modules/model/src/papita_txnsmodel/configs/__init__.py: deleted

  > - modules/model/src/papita_txnsmodel/utils/configutils.py: logger path update

  > 

  > **Views & indexes**

  > - modules/model/src/papita_txnsmodel/views/__init__.py: register MV entities

  > - modules/model/src/papita_txnsmodel/views/base.py: package SQL file reader

  > - modules/model/src/papita_txnsmodel/views/indexes.py: fetch-support index registry

  > - modules/model/src/papita_txnsmodel/views/balance_reports/views.py: PGMaterializedView

  >   definitions

  > - modules/model/src/papita_txnsmodel/views/balance_reports/account_balances.sql: new

  > - modules/model/src/papita_txnsmodel/views/balance_reports/owner_yearly_balances.sql:

  >   new

  > - modules/model/src/papita_txnsmodel/views/balance_reports/owner_monthly_balances.sql:

  >   new

  > - modules/model/src/papita_txnsmodel/views/balance_reports/owner_quarterly_balances.sql:

  >   new

  > - modules/model/src/papita_txnsmodel/views/balance_reports/owner_biannual_balances.sql:

  >   new

  > - modules/model/src/papita_txnsmodel/views/balance_reports/__init__.py: new

  > 

  > **Tests (335 passing)**

  > - modules/model/tests/tests_papita_txnsmodel/access/base/test_owned_table_repository.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/access/categories/test_categories_fr15.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/access/test_balance_report_filters.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/access/test_balance_reports_repository.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/config/test_balance_report_specs.py: new

  > - modules/model/tests/tests_papita_txnsmodel/config/test_materialized_views.py: new

  > - modules/model/tests/tests_papita_txnsmodel/config/test_transaction_partitions.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/database/test_materialized_views.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/handlers/test_balance_reports_handler.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/handlers/test_handlers_v3.py: new

  > - modules/model/tests/tests_papita_txnsmodel/model/test_model_indexes.py: new

  > - modules/model/tests/tests_papita_txnsmodel/services/test_account_balances_refresh.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/services/test_balance_reports.py: new

  > - modules/model/tests/tests_papita_txnsmodel/services/test_owner_period_balances.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/services/test_owner_yearly_balances.py:

  >   new

  > - modules/model/tests/tests_papita_txnsmodel/views/test_indexes.py: new

  > 

  > **Docs, strata, CI tooling**

  > - docs/design/PPT-031-migration-runbook.md: new migration/partitioning runbook

  > - docs/design/README.md: link v3 design artifacts

  > - docs/issues/PPT-031-simplify-requirements.md: align with v3 scope

  > - .strata/docs/ARCHITECTURE.md: codemap for config paths, MVs, partitioning

  > - .strata/memory/project_state.md: session state (335 tests, head revision)

  > - .github/scripts/strata_check.sh: clearer strict-pairing skip messages;

  >   include pyproject.toml in code-path pairing

  > - .pre-commit-config.yaml: exclude docs/coverage.xml from formatters; add

  >   pyproject.toml to strata hook file filter

  > - .cursor/rules/gen-custom/database_migrations.mdc: PostgreSQL-only guidance

  > - .cursor/rules/gen-custom/github_issue_conventions.mdc: new issue naming rules

  > - .gitignore: minor ignore tweak

  > - modules/model/pyproject.toml: add alembic-utils dependency

  > - docs/coverage.xml: regenerated coverage report

  > - docs/interrogate_badge.svg: regenerated badge



- [x] [_**[#41](https://github.com/Elmorralito/save-ma-money/issues/41)**_] :: **Add GitHub Actions security scanning, Strata validation, and local pre-commit guardrails** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 21:59:30+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 22:00:49+00:00</sub>_

  > **Closed by** [_**#40**](https://github.com/Elmorralito/save-ma-money/pull/40): **ci(security): add GitHub security workflows, Strata scaffold, and agent docs**
  >

  > Previously, CI covered quality (pre-commit/pytest), migrations, and supply-chain auditing via pip-audit only. There was no SAST, secret scanning, filesystem CVE/IaC scanning, or validation of agent project memory. Supply-chain path filters still referenced gitignored poetry.lock; quality-control ignored a non-existent .docs/* path.

  > 

  > This change introduces a layered security and documentation gate for PRs: Gitleaks for secrets, CodeQL for Python SAST, Trivy for dependency/IaC misconfig SARIF upload, and Strata layout validation when code paths change. It also scaffolds .strata/ (layout v3), adds AGENTS.md/CLAUDE.md operational adapters, and hardens existing workflows with concurrency groups and pinned action SHAs.

  > 

  > Before → after behavior:

  > - Secret leaks: undetected in CI → full-history Gitleaks scan on every PR

  > - Code vulnerabilities: none → CodeQL security-extended on modules/** changes

  > - CVE/IaC: pip-audit onrivy filesystem scan + SARIF on manifest/docker paths

  > - Agent memory: none → .strata/ scaffold with PR validation (strict module pairing)

  > - Docs-only PRs: ran full QC → skipped via paths-ignore: docs/**

  > - Supply-chain: dead poetry.lock path filter → removed; weekly schedule retained

  > 

  > Changes by file:

  > - .github/workflows/gitleaks.yml: new workflow — PR/push/weekly secret scan; full git history; gitleaks-action pinned to SHA e0c47f4f... (v3)

  > - .github/workflows/codeql.yml: new workflow — Python SAST with Poetry install; path-filtered to modules/**; init/analyze pinned to CodeQL v3 SHA

  > - .github/workflows/trivy.yml: new workflow — filesystem vuln+misconfig scan; trivy-action SHA-pinned (v0.36.0); SARIF upload via upload-sarif v4 SHA; secrets scanner omitted (Gitleaks is primary)

  > - .github/workflows/strata-check.yml: new workflow — validates .strata/ layout on code-path PRs; strict mode requires .strata/ updates when modules/** changes

  > - .github/workflows/quali: fix paths-ignore to docs/**; add concurrency group

  > - .github/workflows/supply-chain-check.yml: remove dead poetry.lock paths; add concurrency, weekly schedule, and workflow_dispatch

  > - .github/scripts/strata_check.sh: new validator — MANIFEST layout_version, file tree, line budgets, issue frontmatter, strict module/strata pairing

  > - .github/scripts/supply_chain_check.sh: reword log (no lock-file reference; poetry.lock is gitignored)

  > - .gitleaks.toml: allowlist .env.example placeholders and template strings

  > - .strata/**: initialize Strata layout v3 scaffold (memory, issues, docs tiers); MANIFEST and ARCHITECTURE customized for this monorepo

  > - AGENTS.md: new operational hub — repo map, layers, env, CI matrix, PR checklist

  > - CLAUDE.md: new thin Claude adapter — session workflow and guardrails

  > - README.md: extend CI table with Gitleaks, CodeQL, Trivy, and Strata Check rows

  > 

  > Snyk and OWASP Dependency-Check were evaluated and intentionally omitted as redundant with pip-audrivy given monorepo constraints and free-tier limits.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#33](https://github.com/Elmorralito/save-ma-money/issues/33)**_] :: **PPT-031-D: API spec realignment to v3 model** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:36+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 21:15:11+00:00</sub>_

  > **Closed by** [_**#39**](https://github.com/Elmorralito/save-ma-money/pull/39): **docs(PPT-031-D)!: align API specs to v3 model and document auth contract**
  >

  > Deliver PPT-031 Track C (#33) and partial Track E (G5): canonical API endpoint mapping to the v3 schema, rewritten integration guide (FR-17), local-JWT auth contract (FR-10/FR-11), and UsersService register/login business logic for #25.

  > 

  > Before: API_Endpoints.md.md used pre-v3 field names (full_name, account_type, budget_id, metadata); no endpoint→model mapping doc; API_Documentation.md.md contradicted the v3 design with phantom fields and active refresh/logout flows; UsersService had no verify_credentials/register path; v1-schema §2 still flagged “needs #33”.

  > 

  > After: All 43 endpoints map 1:1 to v3 tables or explicit 501 deferrals (32 MVP, 11 deferred). Categories → categories table; movements → TRANSFER transaction alias; budgets/split/budget-performance/auth refresh-logout deferred. Auth contract documents HS256 JWT, Argon2, email-or-username login, tenant scoping via JWT sub. Integration guide matches canonical spec.

  > 

  > Changes by file:

  > - docs/design/PPT-031-api-model-mapping.md (new): Endpoint → Service → DTO → SQLModel mapping; field renames; MVP P1–P5 list; report filter rules; FR-07/09/13/17 traceability

  > - docs/design/PPT-031-auth-contract.md (new): Local JWT + users auth strategy; register/login flows; JWT claims; refresh/logout deferred (501); NFR-08 bootstrap; #25 implementation checklist

  > - modules/api/API_Endpoints.md.md: v3 alignment header; auth strategy; account_kind/ledger_side/initial_value; movement currency + validation; report query rules; MVP order; 409/501 errors; expires_in 3600

  > - modules/api/API_Documentation.md.md: Full rewrite as v3 integration guide — removes phantom fields (account_type, budget_id, metadata, sort_by); v3 SDK/cURL examples; defers refresh/logout/budgets

  > - docs/design/README.md: Track C + G3 and Track E + G5 → Written — awaiting sign-off; link new mapping and auth contract docs

  > - docs/design/PPT-031-v1-schema.md: Resolve “needs #33” markers in §2.1– §2.2; link to mapping doc for categories/movements decisions

  > - modules/model/src/papita_txnsmodel/services/users.py: Add ensure_password_manager(), verify_credentials(), register(), and _find_by_login_identifier() (Argon2 verify, duplicate checks, inactive user guard)

  > - modules/model/tests/tests_papita_txnsmodel/services/test_users.py (new): Unit tests for auth methods (9 cases)

  > 

  > Omit from commit: docs/coverage.xml (regenerated by local pytest run).

  > 

  > Closes #33 (Track C deliverables). Unblocks #25 MVP endpoint scope and G3 maintainer sign-off on #28. G5 auth contract written; FastAPI routers still

  > 

  > BREAKING CHANGE: API spec aligned to v3 — register uses username (not full_name); account_type → account_kind; initial_balance → initial_value; budget_id removed from transactions; /budgets/* and /auth/refresh|logout return 501 in MVP; /movements backed by TRANSFER transactions. See docs/design/PPT-031-api-model-mapping.md §8 for consumer migration notes.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#31](https://github.com/Elmorralito/save-ma-money/issues/31)**_] :: **PPT-031-C: Supabase × FastAPI integration decision record** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:35+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 20:45:43+00:00</sub>_

  > **Closed by** [_**#38**](https://github.com/Elmorralito/save-ma-money/pull/38): **docs(PPT-031-C): complete Supabase decision record and deprecate DuckDB upserter**
  >

  > Closes the Track B deliverable for GitHub issue #31 by expanding the skeleton decision brief into a full Supabase × FastAPI integration record, adding a root .env.example template, and aligning registry docs with proposed gate G7 (B0 local Docker Postgres + B1 Supabase for staging/prod; B2/B3 deferred pending G5 auth contract and #34 RLS work). Also deprecates DuckDBUpserter in the code to align with the documented PostgreSQL-only platform decision.

  > 

  > Before: PPT-031-C was an options outline with unchecked deliverables; DuckDB remained documented as a supported dialect, and DuckDBUpserter was still resolved by UpserterFactory for DuckDB sessions.

  > 

  > After: The decision record documents B0–B3 pros/cons, DATABASE_URL formats (transaction vs session pooler), env vars (NFR-05), FastAPI wiring notes, auth/RLS matrices, and an RLS policy sketch. G7 is marked **Proposed** (awaiting maintainer sign-off on #28). DuckDBUpserter emits DeprecationWarning on direct use, and UpserterFactory rejects the duckdb dialect with ValueError.

  > 

  > Changes by file:

  > - .env.example (new): root NFR-05 template for B0/B1 Postgres URLs, JWT, optional Supabase keys, and copy instructions to modules/api/src/.env

  > - docs/issues/PPT-031-C-supabase-decision-brief.md: full decision record — executive decision, platform deprecation table, B0–B3 matrix with phased rollout, DATABASE_URL/SQLAlchemy guidance, env var reference, FastAPI integration notes, auth implications (FR-10/FR-11), B3 RLS outline, completed deliverables checklist, and deferred items (G1, G5, G7 sign-off)

  > - docs/design/README.md: mark Track B / #31 complete (awaiting G7); strengthen platform statement (PostgreSQL only, DuckDB deprecated); set G7 to Proposed

  > - docs/issues/README.md: add status column; mark #31 complete — awaiting G7

  > - README.md: PostgreSQL-only data model wording; link .env.example; warn that unset DATABASE_URL still triggers legacy DuckDB connector fallback

  > - modules/model/README.md: replace DuckDB dialect docs with PostgreSQL-only guidance; note DuckDBUpserter deprecation

  > - modules/model/src/papita_txnsmodel/database/upsert.py: deprecate DuckDBUpserter via warnings.warn(..., DeprecationWarning, stacklevel=2) on __init__ and upsert(); reject duckdb dialect in UpserterFactory

  > - modules/model/tests/tests_papita_txnsmodel/database/test_upsert.py: replace duckdb factory success test with ValueError expectation; add deprecation warning tests for instantiation and upsert

  > 

  > Omit from commit: docs/coverage.xml (regenerated by local pytest run).

  > 

  > Deferred (documented, not implemented): B2 Supabase Auth, B3 RLS migrations, UsersService.verify_credentials, FastAPI main.py/routers (#25), G7 maintainer sign-off on #28.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#32](https://github.com/Elmorralito/save-ma-money/issues/32)**_] :: **PPT-031-B: Target schema iterations v1–v3 + ER diagram** :: _<sub style="vertical-align: middle; color: #636363;">2026-07-02 00:20:35+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-07-06 19:28:43+00:00</sub>_

  > **Closed by** [_**#37**](https://github.com/Elmorralito/save-ma-money/pull/37): **docs(PPT-031-B): add v1–v3 target schema, v4 extensions, and ER diagrams**
  >

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

  > **Closed by** [_**#35**](https://github.com/Elmorralito/save-ma-money/pull/35): **docs(PPT-031-A): Data model audit and 3NF gap analysis (v0)**
  >

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

  >   - §1: link executive summary key findings to §14 register

  >   - §3.14: label transfer/orphan/pair-integrity gaps (NF-01–NF-03);

  >     add handler filter code citation; label sign convention as NF-10

  >   - §9: add NF ID cross-refs and Expert review register row

  >   - §10: add deliverable row for §14 New findings register

  >   - §13: update iteration 5 outcome to reference §14 consolidation

  >   - §14 (new): full findings register (NF-01–NF-12) with per-finding

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

  > **Closed by** [_**#27**](https://github.com/Elmorralito/save-ma-money/pull/27): **Feat/ppt 031**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#5](https://github.com/Elmorralito/save-ma-money/issues/5)**_] :: **feature/PPT-019** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:44:08+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-07 22:44:59+00:00</sub>_


- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#7](https://github.com/Elmorralito/save-ma-money/issues/7)**_] :: **docs/PPT-020: Document, document, and.... document...** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 02:40:49+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-02 23:08:02+00:00</sub>_


- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#10](https://github.com/Elmorralito/save-ma-money/issues/10)**_] :: **docs/PPT-023: API Documentation** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:41:26+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2026-01-02 23:06:15+00:00</sub>_

  > **Closed by** [_**#23**](https://github.com/Elmorralito/save-ma-money/pull/23): **docs(PPT-023): Finishing documentation. TODO: API documentation, it'l…**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#18](https://github.com/Elmorralito/save-ma-money/issues/18)**_] :: **feat/PPT-027: Update the file system accessors to use smart-open instead.** :: _<sub style="vertical-align: middle; color: #636363;">2025-12-22 22:31:51+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 04:07:55+00:00</sub>_

  > **Closed by** [_**#22**](https://github.com/Elmorralito/save-ma-money/pull/22): **feat(PPT-027): Introduce CSV file plugin and CLI support**
  >

  > - Added CSVFilePlugin for loading and processing CSV files, integrating with the transaction tracking system.

  > - Implemented CLICSVFilePlugin to provide command-line interface capabilities for CSV file handling.

  > - Enhanced error handling and argument parsing for improved user experience in CLI operations.

  > - Updated versioning for existing Excel file loader plugins to 1.0.1.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#20](https://github.com/Elmorralito/save-ma-money/issues/20)**_] :: **feat/PPT-028: Add feature to list available plugins** :: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 00:25:15+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 02:42:12+00:00</sub>_

  > **Closed by** [_**#21**](https://github.com/Elmorralito/save-ma-money/pull/21): **feat(PPT-028): Enhance plugin metadata and CLI utilities**
  >

  > - Introduced author information in the plugin metadata model, allowing for detailed author attribution.

  > - Added a new function to list available plugins, enhancing the CLI with the ability to display plugin details.

  > - Updated the registry discovery method to support discovering disabled plugins and improved module handling.

  > - Enhanced error handling and logging in the CLI for better user feedback when listing plugins.



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#14](https://github.com/Elmorralito/save-ma-money/issues/14)**_] :: **test/PPT-025: Unit test design, implementation and code refinement** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-05 20:07:41+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-12-27 01:05:24+00:00</sub>_

  > **Closed by** [_**#19**](https://github.com/Elmorralito/save-ma-money/pull/19): **test(PPT-025)**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#4](https://github.com/Elmorralito/save-ma-money/issues/4)**_] :: **feature/PPT-018** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:29:57+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-11-29 15:46:35+00:00</sub>_

  > **Closed by** [_**#16**](https://github.com/Elmorralito/save-ma-money/pull/16): **feat(PPT-018): Registrar**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#8](https://github.com/Elmorralito/save-ma-money/issues/8)**_] :: **docs/PPT-021: Tracker/Loader Documentation** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:39:56+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-10 01:41:35+00:00</sub>_

  > **Closed by** [_**#15**](https://github.com/Elmorralito/save-ma-money/pull/15): **docs(PPT-021): Defining the design of the tracker/registrar module**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#9](https://github.com/Elmorralito/save-ma-money/issues/9)**_] :: **build/PPT-022: Data model indexer** :: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 15:40:47+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-05 20:03:12+00:00</sub>_

  > **Closed by** [_**#12**](https://github.com/Elmorralito/save-ma-money/pull/12): **build(PPT-022): Data model indexer**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#3](https://github.com/Elmorralito/save-ma-money/issues/3)**_] :: **build/PPT-017** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-19 00:19:36+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-10-01 02:18:51+00:00</sub>_

  > **Closed by** [_**#6**](https://github.com/Elmorralito/save-ma-money/pull/6): **build(PPT-017): Creating CI actions**
  >



- [x] <img src="https://avatars.githubusercontent.com/u/233175807?v=4&s=25" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#1](https://github.com/Elmorralito/save-ma-money/issues/1)**_] :: **feature/PPT-016** :: _<sub style="vertical-align: middle; color: #636363;">2025-09-18 23:46:39+00:00</sub>_ :weary: → :laughing: _<sub style="vertical-align: middle; color: #636363;">2025-09-22 22:16:22+00:00</sub>_

  > **Closed by** [_**#2**](https://github.com/Elmorralito/save-ma-money/pull/2): **feat(PPT-016): Adding data model.**
  >


