# PPT-033: API spec validation against v3 model

| Field           | Value                                                                                              |
| --------------- | -------------------------------------------------------------------------------------------------- |
| **Issue**       | [#43 — Validate API spec against v3 model](https://github.com/Elmorralito/save-ma-money/issues/43) |
| **Parent epic** | [#42 — FastAPI MVP (PPT-032)](https://github.com/Elmorralito/save-ma-money/issues/42)              |
| **Program**     | PPT-031 ([#28](https://github.com/Elmorralito/save-ma-money/issues/28))                            |
| **Date**        | 2026-07-09                                                                                         |
| **Auditor**     | Agent session (PPT-033 execution)                                                                  |

---

## 1. Readiness verdict

**Can #43 close?** **Yes — with this matrix merged.** Prerequisites [#34](https://github.com/Elmorralito/save-ma-money/issues/34) (v3 migration) and [#51](https://github.com/Elmorralito/save-ma-money/issues/51) (PPT-041 model hardening) are **closed**. The canonical API contract in [`modules/api/README.md`](../../modules/api/README.md) aligns with the implemented v3 model in `modules/model`. Remaining gaps are **expected API-layer wiring** (routers, schemas, response shaping) and belong to PPT-034–040 — they do **not** block closing the validation issue.

**Can PPT-034 (#45) start?** **Yes.** Model services, DTOs, migrations, and materialized views are ready. PPT-034 should treat this matrix as the implementation checklist.

| Gate                                 | Status                                     |
| ------------------------------------ | ------------------------------------------ |
| #34 v3 migration applied             | ✅ Closed                                  |
| #51 PPT-041 services + live-DB tests | ✅ Closed                                  |
| FR-17 doc canonical source           | ✅ Unified `modules/api/README.md`         |
| 32 MVP endpoints mapped to model     | ✅ See §4                                  |
| Deferred endpoints marked 501        | ✅ Documented in README                    |
| B0 validation plan                   | ✅ Defined §6                              |
| B1 validation plan                   | ⚠️ Deferred to PPT-039/#50 (env-dependent) |

---

## 2. Executive summary

The v3 model layer implements the domain semantics the API spec requires: `account_kind` / `category_kind` / `transaction_kind`, view-backed `balance`, transfer alias semantics, local JWT auth via `UsersService`, and FR-12 report aggregations via `ReportService`. PPT-041 delivered the service orchestration (#51) that #43 blocked on.

**Doc consolidation (FR-17):** `API_Endpoints.md.md` and `API_Documentation.md.md` are redirect stubs; content lives in the unified [`modules/api/README.md`](../../modules/api/README.md). `README.md - Project Structure.md` is also a redirect. No DuckDB references remain in API docs.

**Primary drift areas** (⚠️ — resolve in API layer, not model):

1. **Response envelope shaping** — `ReportService` returns lean dicts; API spec shows richer JSON (category names, trends insights, `by_account` breakdown).
2. **`POST /transactions/bulk`** — no dedicated `TransactionsService.bulk_create`; use `upsert_records` or add thin wrapper in PPT-037.
3. **Transfer `scheduled` flag** — `create_transfer` always sets `PENDING`; router must set `COMPLETED` when `scheduled: false`.
4. **`account_id` API field** — derivation from `transaction_kind` is an API-schema concern; DTO uses `from_account_id` / `to_account_id`.
5. **Accounts list `balance`** — compose `AccountsService.get_records` + `AccountBalancesService.get_balances` in router/schema layer.
6. **`python-multipart`** — not yet in `modules/api/pyproject.toml` (required before auth routes).

**G1 extension MVP scope (resolved):** Extension tables required for `CHECKING`, `SAVINGS`, `CASH`, `INVESTMENT_BROKERAGE`, `REAL_ESTATE`, `CREDIT_CARD`, `LOAN_MORTGAGE`. `OTHER_ASSET` / `OTHER_LIABILITY` have no extension row. Routed by `account_extension_routing.py` + `AccountsService.create_account`.

---

## 3. Strategy — phased plan

### Phase A — Close #43 (this deliverable) ✅

- [x] Audit model SQLModel, DTOs, services, migrations against API spec
- [x] Publish coverage matrix (this file)
- [x] Record cross-doc findings and B0/B1 validation plan

### Phase B — Doc hygiene (optional small PR)

| Task                                                                                          | Owner issue   | Effort |
| --------------------------------------------------------------------------------------------- | ------------- | ------ |
| Update `PPT-031-api-model-mapping.md` service names (`AccountsService`, not `AccountService`) | #43 follow-up | S      |
| Add pointer in mapping doc §2: canonical spec = `modules/api/README.md`                       | #43 follow-up | S      |
| Link this matrix from #42 epic body and `modules/api/README.md` related docs                  | #43           | S      |

### Phase C — PPT-034 scaffold + health (#45)

- FastAPI `main.py`, lifespan (`UsersService.ensure_password_manager()`)
- Health routers: connector ping + `SELECT 1`
- Add `python-multipart` dependency
- Validate B0: `/health/ready` against Docker Postgres

### Phase D — PPT-035 auth (#44)

- Wire `UsersService.register` / `verify_credentials` + `AuthSecurityManager`
- Map `ValueError` duplicates → HTTP 409 per auth contract
- JWT `sub` = `str(users.id)`; `get_current_user` → `get_owner`

### Phase E — PPT-036–038 domain routers (#46–#48)

- Implement schema converters (`account_type` ↔ `account_kind`, movement field aliases)
- Compose balance reads for account list/detail
- Movement router: honor `scheduled` → status mapping
- Report routers: map `ReportService` payloads to spec response shapes; stub `insights` / `xlsx` / `pdf` where acceptable

### Phase F — PPT-039 / #50 dual-target (#49, #50)

- B1 Supabase pooler `:6543` smoke on health + one CRUD path per domain
- CI integration tests with tenant isolation

---

## 4. Coverage matrix — MVP endpoints (32)

**Legend:** ✅ aligned · ⚠️ partial / API-layer gap · 🔴 missing or blocked

| #                              | Endpoint                  | HTTP   | Key API fields                                                 | Model source                        | Service method                                                        | Doc | Impl | Notes                                                                                                             |
| ------------------------------ | ------------------------- | ------ | -------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------- | --- | ---- | ----------------------------------------------------------------------------------------------------------------- |
| **Health**                     |
| 1                              | `/health`                 | GET    | `status`, `version`, `database`                                | connector ping                      | — (router)                                                            | ✅  | ⚠️   | `SQLDatabaseConnector` exists; no FastAPI app yet                                                                 |
| 2                              | `/health/ready`           | GET    | `ready`                                                        | `SELECT 1`                          | — (router)                                                            | ✅  | ⚠️   | Same; B0/B1 DB ping in PPT-034                                                                                    |
| 3                              | `/health/live`            | GET    | `alive`                                                        | —                                   | — (router)                                                            | ✅  | ⚠️   | Process liveness only                                                                                             |
| **Auth**                       |
| 4                              | `/auth/register`          | POST   | `username`, `email`, `password`                                | `users.*`                           | `UsersService.register`                                               | ✅  | ✅   | No `full_name`; Argon2 via `UsersDTO`; raises `ValueError` on dupes → map to 409 in router                        |
| 5                              | `/auth/login`             | POST   | OAuth2 form `username`, `password`                             | `users.*`                           | `UsersService.verify_credentials` + `AuthSecurityManager`             | ✅  | ✅   | Email or username; JWT `sub` = `users.id` (uuid5)                                                                 |
| **Accounts**                   |
| 6                              | `/accounts`               | GET    | `account_kind`, `currency`, `balance`, filters                 | `accounts` + `account_balances`     | `AccountsService.get_records` + `AccountBalancesService.get_balances` | ✅  | ⚠️   | Balance join is API composition, not single service call                                                          |
| 7                              | `/accounts/{id}`          | GET    | + extension fields                                             | `accounts` + `*_account_details`    | `AccountsService.get_with_extension` + balance                        | ✅  | ✅   | Extension routing by `account_kind` (G1)                                                                          |
| 8                              | `/accounts`               | POST   | `account_kind`, `currency`, `initial_value`, `banking_details` | `accounts`, extensions              | `AccountsService.create_account`                                      | ✅  | ✅   | Extension required for 7 kinds; optional opening INCOME noted in spec                                             |
| 9                              | `/accounts/{id}`          | PUT    | partial update + extensions                                    | `accounts`, extensions              | `AccountsService.update_account`                                      | ✅  | ✅   |                                                                                                                   |
| 10                             | `/accounts/{id}`          | DELETE | soft delete                                                    | `accounts.active`                   | `AccountsService.delete` (soft)                                       | ✅  | ✅   | Via `BaseService.delete`                                                                                          |
| 11                             | `/accounts/{id}/balance`  | GET    | `balance`, `currency`, `as_of`                                 | `account_balances` MV               | `AccountsService.get_balance` → `AccountBalancesService`              | ✅  | ✅   | `last_activity_ts` maps to `as_of`                                                                                |
| **Categories**                 |
| 12                             | `/categories`             | GET    | `category_type`, `parent_id`, `icon`, `color`                  | `categories.category_kind`          | `CategoriesService.get_records`                                       | ✅  | ✅   | No `budget_allocation`; global seeds visible                                                                      |
| 13                             | `/categories/{id}`        | GET    | same                                                           | `categories`                        | `CategoriesService.get`                                               | ✅  | ✅   |                                                                                                                   |
| 14                             | `/categories`             | POST   | `category_type` → `category_kind`                              | `categories`                        | `CategoriesService.create`                                            | ✅  | ✅   | Blocks global writes for tenants                                                                                  |
| 15                             | `/categories/{id}`        | PUT    | same                                                           | `categories`                        | `CategoriesService.create` (upsert)                                   | ✅  | ✅   |                                                                                                                   |
| 16                             | `/categories/{id}`        | DELETE | soft delete                                                    | `categories`                        | `CategoriesService.delete`                                            | ✅  | ✅   |                                                                                                                   |
| **Transactions**               |
| 17                             | `/transactions`           | GET    | `transaction_type`, `account_id` (derived)                     | `transactions`                      | `TransactionsService.get_records` + filter                            | ✅  | ⚠️   | Default exclude TRANSFER = router/repository filter; `account_id` derived in schema                               |
| 18                             | `/transactions/{id}`      | GET    | + `is_recurring` (`template_id`)                               | `transactions`                      | `TransactionsService.get`                                             | ✅  | ✅   |                                                                                                                   |
| 19                             | `/transactions`           | POST   | INCOME/EXPENSE only                                            | `transactions`                      | `TransactionsService.create`                                          | ✅  | ✅   | CHECK constraints enforce account legs; refreshes balance MVs                                                     |
| 20                             | `/transactions/bulk`      | POST   | array of creates                                               | `transactions`                      | `TransactionsService.upsert_records`                                  | ✅  | ⚠️   | No `bulk_create` alias; upsert works — add wrapper in PPT-037                                                     |
| 21                             | `/transactions/{id}`      | PUT    | update                                                         | `transactions`                      | `TransactionsService.create` (upsert)                                 | ✅  | ✅   |                                                                                                                   |
| 22                             | `/transactions/{id}`      | DELETE | soft delete                                                    | `transactions`                      | `TransactionsService.delete`                                          | ✅  | ✅   | Refreshes balance MVs                                                                                             |
| **Movements (TRANSFER alias)** |
| 23                             | `/movements`              | GET    | `source_account_id`, `destination_account_id`                  | `transactions` (`kind=TRANSFER`)    | `TransactionsService.list_transfers`                                  | ✅  | ✅   |                                                                                                                   |
| 24                             | `/movements/{id}`         | GET    | movement field names                                           | `transactions`                      | `TransactionsService.get`                                             | ✅  | ⚠️   | Field rename in API `MovementDTO` / converter                                                                     |
| 25                             | `/movements`              | POST   | `scheduled` → status                                           | `transactions`                      | `TransactionsService.create_transfer`                                 | ✅  | ⚠️   | Service always PENDING; router sets COMPLETED when `scheduled: false`                                             |
| 26                             | `/movements/{id}`         | PUT    | PENDING only                                                   | `transactions`                      | `TransactionsService.create`                                          | ✅  | ✅   | Status guard in router                                                                                            |
| 27                             | `/movements/{id}`         | DELETE | cancel PENDING                                                 | `transactions.status`               | `TransactionsService.cancel`                                          | ✅  | ✅   | Sets CANCELLED, not soft delete                                                                                   |
| 28                             | `/movements/{id}/execute` | POST   | `status=completed`                                             | `transactions`                      | `TransactionsService.complete_transfer`                               | ✅  | ✅   |                                                                                                                   |
| **Reports**                    |
| 29                             | `/reports/spending`       | GET    | expense/income totals, breakdown                               | `transactions` + `categories`       | `ReportService.spending`                                              | ✅  | ⚠️   | Service: `group_by` category/account only; API also documents day/week/month — enrich in router or extend service |
| 30                             | `/reports/cash-flow`      | GET    | inflows, outflows, balances                                    | `transactions` + `account_balances` | `ReportService.cash_flow`                                             | ✅  | ⚠️   | Service lacks `opening_balance`, `closing_balance`, `by_account` — API schema maps/enriches                       |
| 31                             | `/reports/trends`         | GET    | time series                                                    | `transactions`                      | `ReportService.trends`                                                | ✅  | ⚠️   | Service lacks `insights`, `category_trends`, `savings_rate` — stub or compute in API                              |
| 32                             | `/reports/export`         | GET    | CSV delegate                                                   | above                               | `ReportService.export`                                                | ✅  | ⚠️   | Service: csv/json only; spec mentions xlsx/pdf — return 501 or stub                                               |

### Deferred endpoints (501 — not in MVP count)

| Endpoint                          | Doc status        | Impl | Notes                           |
| --------------------------------- | ----------------- | ---- | ------------------------------- |
| `POST /auth/refresh`              | ✅ Deferred FR-11 | N/A  | Return 501 or omit from OpenAPI |
| `POST /auth/logout`               | ✅ Deferred FR-11 | N/A  |                                 |
| `/budgets/*` (7 routes)           | ✅ Deferred FR-09 | N/A  | No v3 tables                    |
| `POST /transactions/{id}/split`   | ✅ Deferred v4    | N/A  |                                 |
| `GET /reports/budget-performance` | ✅ Deferred FR-09 | N/A  |                                 |

---

## 5. Field mapping audit (#43 checklist)

| Domain       | Required mapping                                  | Doc (README) | Model / service                            | Status                            |
| ------------ | ------------------------------------------------- | ------------ | ------------------------------------------ | --------------------------------- |
| Accounts     | `account_kind`, `currency`, `initial_value`       | ✅           | `AccountsDTO`, `accounts` table            | ✅                                |
| Accounts     | `balance` from `account_balances` MV              | ✅           | `AccountBalancesService`, MV in Alembic    | ✅                                |
| Categories   | `category_kind` (not `types`)                     | ✅           | `CategoriesDTO`, `categories` table        | ✅                                |
| Categories   | no `budget_allocation`                            | ✅           | Field absent                               | ✅                                |
| Transactions | `transaction_kind`; account leg derivation        | ✅           | `TransactionsDTO` + DB CHECK               | ⚠️ API converter for `account_id` |
| Movements    | alias over TRANSFER rows                          | ✅           | `list_transfers`, `create_transfer`, etc.  | ✅                                |
| Auth         | `username` + `email` + `password`; no `full_name` | ✅           | `UsersDTO`, `UsersService`                 | ✅                                |
| Auth         | JWT `sub` = `users.id`                            | ✅           | uuid5 from username; `AuthSecurityManager` | ✅                                |

### Enum slug convention

| API (JSON)                          | DB (PostgreSQL)                     | Documented               | Converter location                 |
| ----------------------------------- | ----------------------------------- | ------------------------ | ---------------------------------- |
| `expense`, `income`, `transfer`     | `EXPENSE`, `INCOME`, `TRANSFER`     | ✅ README + mapping §4.3 | `papita_txnsapi/schemas/` (target) |
| `checking`, `savings`, …            | `CHECKING`, `SAVINGS`, …            | ✅                       | schemas/converters (target)        |
| `pending`, `completed`, `cancelled` | `PENDING`, `COMPLETED`, `CANCELLED` | ✅                       | schemas/converters (target)        |

---

## 6. Service availability (post-#51)

| Service                  | Methods required by mapping                                                   | Implemented | Tests                                  |
| ------------------------ | ----------------------------------------------------------------------------- | ----------- | -------------------------------------- |
| `UsersService`           | `register`, `verify_credentials`, `get_owner`, `ensure_password_manager`      | ✅          | `test_users.py`                        |
| `AccountsService`        | `create_account`, `update_account`, `get_with_extension`, `get_balance`, CRUD | ✅          | `test_ppt041_services.py`              |
| `AccountBalancesService` | `get_balance`, `get_balances`, `refresh`                                      | ✅          | balance report tests                   |
| `CategoriesService`      | CRUD + global write guard                                                     | ✅          | `test_ppt041_services.py`, FR-15 tests |
| `TransactionsService`    | CRUD, `list_transfers`, `create_transfer`, `complete_transfer`, `cancel`      | ✅          | `test_ppt041_services.py`              |
| `ReportService`          | `spending`, `cash_flow`, `trends`, `export`                                   | ✅          | `test_ppt041_services.py`              |
| `AuthSecurityManager`    | `generate_token`, `decode_token`, `authenticate_and_get_token`                | ✅          | API unit tests TBD (#50)               |

---

## 7. Cross-doc consistency (FR-17)

| Check                                          | Result                                                                                          |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Endpoints spec vs integration guide contradict | ✅ **None** — merged into single README                                                         |
| Enum slug mapping in both docs                 | ✅ README §Overview + §Integration guide                                                        |
| Deferred endpoints marked 501                  | ✅ README throughout                                                                            |
| DuckDB in API README / Project Structure       | ✅ **Removed** — redirects only; PostgreSQL-only stated                                         |
| Mapping doc §5 service names match code        | ⚠️ Uses `AccountService`, `CategoryService`, `TransactionService` (singular) — code uses plural |
| Issue #43 references `API_Endpoints.md.md`     | ⚠️ File is redirect stub — update issue template to cite README                                 |

---

## 8. Platform validation plan (B0 + B1)

### B0 — Docker Postgres (PPT-034 gate)

Run after `./deploy/alembic.sh upgrade --docker-local`:

| Validation        | Command / check                           | Matrix rows   |
| ----------------- | ----------------------------------------- | ------------- |
| Schema + MV exist | `\d papita_transactions.account_balances` | 6, 11, 29–31  |
| Health ready      | `GET /health/ready` → DB connected        | 1–3           |
| Auth round-trip   | register → login → JWT decode             | 4–5           |
| Account + balance | create account → GET balance from MV      | 8, 11         |
| Transfer alias    | POST movement → row with `TRANSFER`       | 25, 28        |
| Report query      | `ReportService.spending` with seeded data | 29            |
| Tenancy isolation | existing `test_tenancy_live_db.py`        | all protected |

### B1 — Supabase pooler `:6543` (PPT-039 / #50)

| Validation                         | When    | Notes                                    |
| ---------------------------------- | ------- | ---------------------------------------- |
| Migration applied on hosted DB     | PPT-039 | Use `DATABASE_URL_MIGRATIONS` on `:5432` |
| Pooler connectivity                | PPT-039 | `DATABASE_URL` on `:6543`                |
| `/health/ready`                    | PPT-039 | Same app, different URL                  |
| View-backed balance read           | PPT-039 | Confirm MV refresh + read on pooler      |
| Live-DB tests (optional CI secret) | #50     | Mirror B0 matrix with B1 URL             |

---

## 9. Gap inventory → follow-on issues

| Gap                                | Severity         | Absorb in     | Action                                               |
| ---------------------------------- | ---------------- | ------------- | ---------------------------------------------------- |
| No FastAPI app / routers           | Expected         | PPT-034 #45   | Scaffold `main.py`, health                           |
| `python-multipart` missing         | Blocker for auth | PPT-034 #45   | Add to `modules/api/pyproject.toml`                  |
| Auth HTTP status mapping           | Low              | PPT-035 #44   | Map `ValueError` → 409                               |
| Account list balance join          | Medium           | PPT-036 #46   | Compose in router or add `list_with_balances` helper |
| `account_id` ↔ leg derivation      | Medium           | PPT-037 #47   | `schemas/converters.py`                              |
| `bulk_create` wrapper              | Low              | PPT-037 #47   | Thin wrapper over `upsert_records`                   |
| TRANSFER list default exclude      | Low              | PPT-037 #47   | Repository filter in router                          |
| Movement `scheduled` status        | Medium           | PPT-037 #47   | Router sets status after `create_transfer`           |
| Report response enrichment         | Medium           | PPT-038 #48   | API schemas map service dicts → spec JSON            |
| Report `group_by` day/week/month   | Low              | PPT-038 #48   | Extend `ReportService` or stub in API                |
| Export xlsx/pdf                    | Low              | PPT-038 #48   | 501 for non-CSV in MVP                               |
| Mapping doc singular service names | Low              | #43 follow-up | Doc-only fix                                         |
| B1 pooler smoke                    | Medium           | PPT-039 #49   | Env + CI                                             |
| API integration tests              | Medium           | PPT-040 #50   | Router tests on B0 (+ B1 optional)                   |

---

## 10. Top gaps (highest impact)

| Rank | Gap                                  | Status | Blocks PPT-034?           |
| ---- | ------------------------------------ | ------ | ------------------------- |
| 1    | FastAPI scaffold absent              | 🔴     | No — that's PPT-034 scope |
| 2    | `python-multipart` not in API deps   | ⚠️     | Yes — add in first API PR |
| 3    | Report API response vs service shape | ⚠️     | No — PPT-038              |
| 4    | Movement `scheduled` → status        | ⚠️     | No — PPT-037 router logic |
| 5    | Account list balance composition     | ⚠️     | No — PPT-036              |
| 6    | Mapping doc service name drift       | ⚠️     | No — doc-only             |

---

## 11. Next concrete step

**Start PPT-034 (#45):** Create `modules/api/src/papita_txnsapi/main.py` with lifespan bootstrap, mount health router, add `python-multipart`, and validate `/health/ready` on Docker Postgres (B0).

---

## References

- Canonical API spec: [`modules/api/README.md`](../../modules/api/README.md)
- API ↔ model mapping: [`PPT-031-api-model-mapping.md`](PPT-031-api-model-mapping.md)
- Auth contract: [`PPT-031-auth-contract.md`](PPT-031-auth-contract.md)
- Model services: `modules/model/src/papita_txnsmodel/services/`
- PPT-041 tests: `modules/model/tests/tests_papita_txnsmodel/services/test_ppt041_services.py`
- Live-DB tenancy: `modules/model/tests/tests_papita_txnsmodel/integration/test_tenancy_live_db.py`
- Epic: [#42](https://github.com/Elmorralito/save-ma-money/issues/42)
