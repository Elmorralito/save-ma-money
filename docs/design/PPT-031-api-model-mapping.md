# PPT-031: API ↔ v3 Model Mapping

| Field      | Value                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------- |
| **Issue**  | [#33 — API spec realignment to v3 model](https://github.com/Elmorralito/save-ma-money/issues/33)              |
| **Parent** | [#28 — refactor/PPT-031](https://github.com/Elmorralito/save-ma-money/issues/28)                              |
| **Input**  | [#32 v3 schema](PPT-031-v1-schema.md), [#30 v0 audit](PPT-031-v0-audit.md), `modules/api/API_Endpoints.md.md` |
| **Track**  | C — API spec realignment                                                                                      |
| **Date**   | 2026-07-06                                                                                                    |
| **Status** | **Written** — awaiting G3 sign-off on [#28](https://github.com/Elmorralito/save-ma-money/issues/28)           |

---

## 1. Executive summary

This document maps every endpoint in the canonical API spec (`modules/api/API_Endpoints.md.md`) to the **v3 target schema** defined in [`PPT-031-v1-schema.md`](PPT-031-v1-schema.md) §3. It unblocks [#25](https://github.com/Elmorralito/save-ma-money/issues/25) API CRUD implementation and satisfies **FR-07**, **FR-09**, **FR-13**, and **FR-17**.

### Key decisions (resolved)

| #33 open item                              | Resolution                                                               | Rationale                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `/categories/*` → `types`                  | **Keep `/categories/*`**; map to new `categories` table                  | v0 `types` is dropped; API vocabulary matches user domain (FR-13)                         |
| `/movements/*`                             | **Router alias** over `transactions` where `transaction_kind = TRANSFER` | No `movements` table; same persistence layer (FR-05, NF-01)                               |
| `/budgets/*`                               | **Deferred** post-MVP (v4.1)                                             | No v3 tables; design in [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) §4 (FR-09) |
| `/auth/register` `full_name` vs `username` | **Use `username` + `email` + `password`**                                | Aligns with `Users` SQLModel and `UsersDTO` validators (FR-10)                            |

### MVP scope summary

| Scope                                   | Endpoints                                                                                                       | Count  |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------ |
| **MVP** (implement in #25)              | Health (3), auth register/login (2), accounts (6), categories (5), transactions (6), movements (6), reports (4) | **32** |
| **Deferred** (501 or omit from OpenAPI) | Budgets (7), auth refresh/logout (2), transaction split (1), reports/budget-performance (1)                     | **11** |
| **Total**                               |                                                                                                                 | **43** |

---

## 2. Architecture layers

```
HTTP Request
  → FastAPI Router          (papita_txnsapi/routers/)
  → Pydantic API Schema     (papita_txnsapi/schemas/)   — request/response only; no business rules
  → Service                 (papita_txnsmodel/services/) — business logic, DTO validation
  → Repository              (papita_txnsmodel/access/*/repository.py)
  → DTO                     (papita_txnsmodel/access/*/dto.py)
  → SQLModel                (papita_txnsmodel/model/)
  → PostgreSQL              (schema: papita_transactions)
```

**FR-17 rules:**

- `API_Endpoints.md.md` is the **canonical human-readable spec** for endpoint contracts until FastAPI `main.py` ships; then OpenAPI JSON from the running app becomes the runtime source of truth.
- `API_Documentation.md.md` is the **v3-aligned integration guide** (auth flows, SDK patterns, data shapes) — must not contradict `API_Endpoints.md.md`.
- API schemas map 1:1 to model DTOs; validators live in DTOs, not duplicated in API layer.
- Add `python-multipart` to `modules/api/pyproject.toml` before implementing OAuth2 form login.

---

## 3. v3 table inventory (reference)

| v3 table / view                | Replaces (v0)                         | Tenant-scoped         |
| ------------------------------ | ------------------------------------- | --------------------- |
| `users`                        | —                                     | root                  |
| `accounts`                     | `accounts` + indexer + subtype tables | ✓ `owner_id`          |
| `banking_account_details`      | `banking_asset_accounts`              | via `account_id`      |
| `real_estate_account_details`  | `real_estate_asset_accounts`          | via `account_id`      |
| `trading_account_details`      | `trading_asset_accounts`              | via `account_id`      |
| `credit_card_account_details`  | `credit_card_liability_accounts`      | via `account_id`      |
| `loan_account_details`         | `bank_credit_liability_accounts`      | via `account_id`      |
| `account_financing`            | `financed_asset_accounts`             | ✓ `owner_id`          |
| `categories`                   | `types` (TRANSACTIONS classification) | ✓ `owner_id` nullable |
| `transaction_templates`        | `identified_transactions`             | ✓ `owner_id`          |
| `transactions`                 | `transactions`                        | ✓ `owner_id`          |
| `account_balances` (mat. view) | — (phantom `balance` column)          | ✓                     |

---

## 4. Field mapping reference

### 4.1 Accounts

| API field           | v3 column / source                | Notes                                                                           |
| ------------------- | --------------------------------- | ------------------------------------------------------------------------------- |
| `account_type`      | `accounts.account_kind`           | API uses lowercase slug; map to enum (`checking` → `CHECKING`)                  |
| `currency`          | `accounts.currency`               | ISO 4217 `CHAR(3)`                                                              |
| `balance`           | `account_balances.balance`        | Read from materialized view, not stored on `accounts`                           |
| `initial_balance`   | `accounts.initial_value`          | Write on create; optional opening-balance transaction                           |
| `is_active`         | `accounts.active`                 | BaseSQLModel soft-delete companion                                              |
| `metadata`          | extension tables                  | Banking/real-estate fields → `*_account_details`; drop generic JSON blob in MVP |
| `opened_at` / dates | `accounts.opened_at`, `closed_at` | was `start_ts` / `end_ts`                                                       |

### 4.2 Categories

| API field           | v3 column                             | Notes                                            |
| ------------------- | ------------------------------------- | ------------------------------------------------ |
| `category_type`     | `categories.category_kind`            | API `income`/`expense` ↔ enum `INCOME`/`EXPENSE` |
| `parent_id`         | `categories.parent_id`                | Self-FK hierarchy                                |
| `subcategories`     | computed                              | Child rows via `parent_id`; not stored           |
| `budget_allocation` | —                                     | **Removed** — budgets deferred                   |
| `icon`, `color`     | `categories.icon`, `categories.color` | New v3 columns                                   |

### 4.3 Transactions

| API field                 | v3 column                       | Notes                                                                                   |
| ------------------------- | ------------------------------- | --------------------------------------------------------------------------------------- |
| `transaction_type`        | `transactions.transaction_kind` | `income`/`expense`/`transfer` ↔ `INCOME`/`EXPENSE`/`TRANSFER`                           |
| `account_id`              | derived                         | INCOME → `to_account_id`; EXPENSE → `from_account_id`; TRANSFER → both                  |
| `transaction_date`        | `transactions.transaction_ts`   |                                                                                         |
| `budget_id`               | —                               | **Removed** — budgets deferred                                                          |
| `is_recurring`            | computed                        | `template_id IS NOT NULL`                                                               |
| `recurrence_rule`         | —                               | Deferred; templates use `planned_day`                                                   |
| `attachments`, `metadata` | —                               | Deferred (v4)                                                                           |
| `status`                  | `transactions.status`           | API lowercase: `pending`/`completed`/`cancelled`; DB: `PENDING`/`COMPLETED`/`CANCELLED` |

**API enum convention:** JSON request/response bodies use **lowercase slugs**; PostgreSQL stores **uppercase** enum values. Converters in `papita_txnsapi/schemas/` handle mapping.

### 4.4 Movements (TRANSFER alias)

| API field                | v3 column                      | Notes                                          |
| ------------------------ | ------------------------------ | ---------------------------------------------- |
| `source_account_id`      | `transactions.from_account_id` | Filter `transaction_kind = TRANSFER`           |
| `destination_account_id` | `transactions.to_account_id`   |                                                |
| `amount`                 | `transactions.amount`          | Always positive                                |
| `currency`               | `transactions.currency`        | Required; must match both accounts' `currency` |
| `movement_date`          | `transactions.transaction_ts`  |                                                |
| `scheduled`              | `status = PENDING`             |                                                |
| `execute` action         | PATCH `status` → `COMPLETED`   | Sets `transaction_ts` if unset                 |

### 4.5 Auth

Full contract: [`PPT-031-auth-contract.md`](PPT-031-auth-contract.md).

| API field                   | v3 column                     | Notes                                   |
| --------------------------- | ----------------------------- | --------------------------------------- |
| `username` (register)       | `users.username`              | min 6 chars, unique                     |
| `email`                     | `users.email`                 | unique                                  |
| `password`                  | `users.password`              | Argon2 hash via `UsersDTO._serialize()` |
| `full_name`                 | —                             | **Removed** — use `username`            |
| JWT `sub`                   | `users.id`                    | UUID string; uuid5 from username hash   |
| Login `username` form field | email **or** username         | `UsersService.verify_credentials()`     |
| `expires_in`                | `JWT_EXPIRATION_TIME_SECONDS` | Default 3600                            |

**Service methods (implemented):**

| Method                                                  | Purpose                                   |
| ------------------------------------------------------- | ----------------------------------------- |
| `UsersService.ensure_password_manager()`                | Bootstrap Argon2 (lifespan + auth routes) |
| `UsersService.register(username, email, password)`      | Uniqueness checks + create                |
| `UsersService.verify_credentials(identifier, password)` | Login verification → `UsersDTO \| None`   |
| `UsersService.get_owner(owner_id)`                      | Resolve JWT `sub` for tenant scope        |
| `AuthSecurityManager.generate_token(user_id)`           | Issue JWT                                 |
| `AuthSecurityManager.decode_token(token)`               | Validate JWT on protected routes          |

---

## 5. Endpoint mapping (complete)

**Legend:** MVP = implement in #25; **Deferred** = return 501 or exclude from MVP OpenAPI; **Alias** = separate router, same service/table.

### 5.1 Health

| Method | Path            | Router          | Service | Repository | DTO | SQLModel                 | MVP  |
| ------ | --------------- | --------------- | ------- | ---------- | --- | ------------------------ | ---- |
| GET    | `/health`       | `health.router` | —       | —          | —   | — (connector ping)       | ✓ P1 |
| GET    | `/health/ready` | `health.router` | —       | —          | —   | `SELECT 1` via connector | ✓ P1 |
| GET    | `/health/live`  | `health.router` | —       | —          | —   | —                        | ✓ P1 |

### 5.2 Authentication

| Method | Path             | Router        | Service                                                   | Repository        | DTO        | SQLModel | MVP                                                         |
| ------ | ---------------- | ------------- | --------------------------------------------------------- | ----------------- | ---------- | -------- | ----------------------------------------------------------- |
| POST   | `/auth/register` | `auth.router` | `UsersService.register`                                   | `UsersRepository` | `UsersDTO` | `users`  | ✓ P2                                                        |
| POST   | `/auth/login`    | `auth.router` | `UsersService.verify_credentials` + `AuthSecurityManager` | `UsersRepository` | `UsersDTO` | `users`  | ✓ P2                                                        |
| POST   | `/auth/refresh`  | `auth.router` | —                                                         | —                 | —          | —        | **Deferred** (FR-11: stateless JWT; no refresh token store) |
| POST   | `/auth/logout`   | `auth.router` | —                                                         | —                 | —          | —        | **Deferred** (FR-11: no revocation denylist in MVP)         |

### 5.3 Accounts

| Method | Path                             | Router            | Service                      | Repository          | DTO                           | SQLModel                             | MVP  |
| ------ | -------------------------------- | ----------------- | ---------------------------- | ------------------- | ----------------------------- | ------------------------------------ | ---- |
| GET    | `/accounts`                      | `accounts.router` | `AccountService`             | `AccountRepository` | `AccountDTO`                  | `accounts` + `account_balances` join | ✓ P3 |
| GET    | `/accounts/{account_id}`         | `accounts.router` | `AccountService`             | `AccountRepository` | `AccountDTO`                  | `accounts` + extensions              | ✓ P3 |
| POST   | `/accounts`                      | `accounts.router` | `AccountService`             | `AccountRepository` | `AccountDTO` + extension DTOs | `accounts`, `*_account_details`      | ✓ P3 |
| PUT    | `/accounts/{account_id}`         | `accounts.router` | `AccountService`             | `AccountRepository` | `AccountDTO`                  | `accounts`                           | ✓ P3 |
| DELETE | `/accounts/{account_id}`         | `accounts.router` | `AccountService.soft_delete` | `AccountRepository` | —                             | `accounts` (`active=false`)          | ✓ P3 |
| GET    | `/accounts/{account_id}/balance` | `accounts.router` | `AccountService.get_balance` | —                   | —                             | `account_balances` view              | ✓ P3 |

**v3 service notes:** `AccountService` replaces v0 `AccountsService` + `IndexersService` + subtype services. Extension table writes keyed by `account_kind`.

### 5.4 Categories

| Method | Path                        | Router              | Service                       | Repository             | DTO           | SQLModel     | MVP  |
| ------ | --------------------------- | ------------------- | ----------------------------- | ---------------------- | ------------- | ------------ | ---- |
| GET    | `/categories`               | `categories.router` | `CategoryService`             | `CategoriesRepository` | `CategoryDTO` | `categories` | ✓ P4 |
| GET    | `/categories/{category_id}` | `categories.router` | `CategoryService`             | `CategoriesRepository` | `CategoryDTO` | `categories` | ✓ P4 |
| POST   | `/categories`               | `categories.router` | `CategoryService`             | `CategoriesRepository` | `CategoryDTO` | `categories` | ✓ P4 |
| PUT    | `/categories/{category_id}` | `categories.router` | `CategoryService`             | `CategoriesRepository` | `CategoryDTO` | `categories` | ✓ P4 |
| DELETE | `/categories/{category_id}` | `categories.router` | `CategoryService.soft_delete` | `CategoriesRepository` | —             | `categories` | ✓ P4 |

**FR-13:** Expense/income taxonomy only. v0 `types` with `ASSETS`/`LIABILITIES` classification is replaced by `accounts.account_kind` — not exposed via `/categories`.

**FR-15:** ID = `uuid5(owner_id|parent_id|name|category_kind)`. Global seeds (`owner_id IS NULL`) are read-only for tenants.

### 5.5 Budgets — **Deferred (FR-09)**

| Method | Path                               | Router           | Service | Repository | DTO | SQLModel                  | MVP          |
| ------ | ---------------------------------- | ---------------- | ------- | ---------- | --- | ------------------------- | ------------ |
| GET    | `/budgets`                         | `budgets.router` | —       | —          | —   | — (v4.1 `budgets`)        | **Deferred** |
| GET    | `/budgets/{budget_id}`             | `budgets.router` | —       | —          | —   | —                         | **Deferred** |
| POST   | `/budgets`                         | `budgets.router` | —       | —          | —   | —                         | **Deferred** |
| PUT    | `/budgets/{budget_id}`             | `budgets.router` | —       | —          | —   | —                         | **Deferred** |
| DELETE | `/budgets/{budget_id}`             | `budgets.router` | —       | —          | —   | —                         | **Deferred** |
| GET    | `/budgets/{budget_id}/summary`     | `budgets.router` | —       | —          | —   | —                         | **Deferred** |
| POST   | `/budgets/{budget_id}/allocations` | `budgets.router` | —       | —          | —   | v4.1 `budget_allocations` | **Deferred** |

**Future design:** [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) §4.1. MVP returns **501 Not Implemented** if route is mounted, or route omitted from OpenAPI.

### 5.6 Transactions

| Method | Path                                   | Router                | Service                          | Repository              | DTO                | SQLModel                | MVP          |
| ------ | -------------------------------------- | --------------------- | -------------------------------- | ----------------------- | ------------------ | ----------------------- | ------------ |
| GET    | `/transactions`                        | `transactions.router` | `TransactionService`             | `TransactionRepository` | `TransactionDTO`   | `transactions`          | ✓ P4         |
| GET    | `/transactions/{transaction_id}`       | `transactions.router` | `TransactionService`             | `TransactionRepository` | `TransactionDTO`   | `transactions`          | ✓ P4         |
| POST   | `/transactions`                        | `transactions.router` | `TransactionService`             | `TransactionRepository` | `TransactionDTO`   | `transactions`          | ✓ P4         |
| POST   | `/transactions/bulk`                   | `transactions.router` | `TransactionService.bulk_create` | `TransactionRepository` | `TransactionDTO[]` | `transactions`          | ✓ P4         |
| PUT    | `/transactions/{transaction_id}`       | `transactions.router` | `TransactionService`             | `TransactionRepository` | `TransactionDTO`   | `transactions`          | ✓ P4         |
| DELETE | `/transactions/{transaction_id}`       | `transactions.router` | `TransactionService.soft_delete` | `TransactionRepository` | —                  | `transactions`          | ✓ P4         |
| POST   | `/transactions/{transaction_id}/split` | `transactions.router` | —                                | —                       | —                  | v4 `transaction_splits` | **Deferred** |

**Query filter:** `transaction_type=transfer` on `/transactions` returns same rows as `/movements/*`. Default list excludes `TRANSFER` unless filter includes it (avoid duplicate listing when both routers mounted).

**Templates:** Recurring/planned entries use `transaction_templates` table. Optional nested resource `/transaction-templates/*` post-MVP; MVP links via `template_id` on transaction responses.

### 5.7 Movements — **Alias router**

| Method | Path                               | Router             | Service                                | Repository              | DTO                                    | SQLModel                            | MVP            |
| ------ | ---------------------------------- | ------------------ | -------------------------------------- | ----------------------- | -------------------------------------- | ----------------------------------- | -------------- |
| GET    | `/movements`                       | `movements.router` | `TransactionService.list_transfers`    | `TransactionRepository` | `MovementDTO` (API) → `TransactionDTO` | `transactions` (`kind=TRANSFER`)    | ✓ P4 **Alias** |
| GET    | `/movements/{movement_id}`         | `movements.router` | `TransactionService.get`               | `TransactionRepository` | `MovementDTO`                          | `transactions`                      | ✓ P4 **Alias** |
| POST   | `/movements`                       | `movements.router` | `TransactionService.create_transfer`   | `TransactionRepository` | `TransactionDTO`                       | `transactions`                      | ✓ P4 **Alias** |
| PUT    | `/movements/{movement_id}`         | `movements.router` | `TransactionService.update`            | `TransactionRepository` | `TransactionDTO`                       | `transactions`                      | ✓ P4 **Alias** |
| DELETE | `/movements/{movement_id}`         | `movements.router` | `TransactionService.cancel`            | `TransactionRepository` | —                                      | `transactions` (`status=CANCELLED`) | ✓ P4 **Alias** |
| POST   | `/movements/{movement_id}/execute` | `movements.router` | `TransactionService.complete_transfer` | `TransactionRepository` | —                                      | `transactions` (`status=COMPLETED`) | ✓ P4 **Alias** |

**Implementation pattern:** `movements.router` delegates to `TransactionService` with `transaction_kind=TRANSFER` enforced. `MovementDTO` is a Pydantic API schema that maps field names (`source_account_id` ↔ `from_account_id`).

### 5.8 Reports (read models — FR-12)

| Method | Path                          | Router           | Service                   | Repository | DTO | SQLModel / view                                  | MVP            |
| ------ | ----------------------------- | ---------------- | ------------------------- | ---------- | --- | ------------------------------------------------ | -------------- |
| GET    | `/reports/spending`           | `reports.router` | `ReportService.spending`  | —          | —   | `transactions` + `categories`                    | ✓ P5 (query)   |
| GET    | `/reports/budget-performance` | `reports.router` | —                         | —          | —   | v4 `budgets`                                     | **Deferred**   |
| GET    | `/reports/cash-flow`          | `reports.router` | `ReportService.cash_flow` | —          | —   | `transactions` + `accounts` + `account_balances` | ✓ P5 (query)   |
| GET    | `/reports/trends`             | `reports.router` | `ReportService.trends`    | —          | —   | `transactions` time-series                       | ✓ P5 (query)   |
| GET    | `/reports/export`             | `reports.router` | `ReportService.export`    | —          | —   | Above queries                                    | ✓ P5 (stub OK) |

**Read-model strategy:** Service-layer SQL aggregations; no report tables in v3. Refresh `account_balances` materialized view before balance-dependent reports ([#34](https://github.com/Elmorralito/save-ma-money/issues/34) runbook).

| Report               | Filter rules                                                                                                                             |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `/reports/spending`  | `transaction_kind = EXPENSE`, `status = COMPLETED` for spending breakdown; income totals from `INCOME` rows separately; exclude TRANSFER |
| `/reports/cash-flow` | `status = COMPLETED` only; inflows/outflows include TRANSFER legs; portfolio balances sum `account_balances`                             |
| `/reports/trends`    | `EXPENSE` + `INCOME`, `COMPLETED`; time-series by `transaction_ts`                                                                       |
| `/reports/export`    | Delegates to above; CSV stub acceptable in MVP                                                                                           |

---

## 6. MVP endpoint list for [#25](https://github.com/Elmorralito/save-ma-money/issues/25)

Implementation order after **G1 v3 schema sign-off** ([#28](https://github.com/Elmorralito/save-ma-money/issues/28)).

| Priority | Method | Path                               | Notes                                                               |
| -------- | ------ | ---------------------------------- | ------------------------------------------------------------------- |
| **P1**   | GET    | `/health`                          | App + version                                                       |
| **P1**   | GET    | `/health/ready`                    | DB `SELECT 1`                                                       |
| **P1**   | GET    | `/health/live`                     | Process liveness                                                    |
| **P2**   | POST   | `/auth/register`                   | `username`, `email`, `password`; bootstrap `PasswordManagerFactory` |
| **P2**   | POST   | `/auth/login`                      | OAuth2 form; login by email or username                             |
| **P3**   | GET    | `/accounts`                        | Include `balance` from view                                         |
| **P3**   | GET    | `/accounts/{account_id}`           |                                                                     |
| **P3**   | POST   | `/accounts`                        | `account_kind`, `currency`, `initial_value`                         |
| **P3**   | PUT    | `/accounts/{account_id}`           |                                                                     |
| **P3**   | DELETE | `/accounts/{account_id}`           | Soft delete                                                         |
| **P3**   | GET    | `/accounts/{account_id}/balance`   | `account_balances` view                                             |
| **P4**   | GET    | `/categories`                      | Tenant + global seeds                                               |
| **P4**   | GET    | `/categories/{category_id}`        |                                                                     |
| **P4**   | POST   | `/categories`                      |                                                                     |
| **P4**   | PUT    | `/categories/{category_id}`        |                                                                     |
| **P4**   | DELETE | `/categories/{category_id}`        |                                                                     |
| **P4**   | GET    | `/transactions`                    | Exclude TRANSFER by default                                         |
| **P4**   | GET    | `/transactions/{transaction_id}`   |                                                                     |
| **P4**   | POST   | `/transactions`                    | INCOME/EXPENSE only                                                 |
| **P4**   | POST   | `/transactions/bulk`               |                                                                     |
| **P4**   | PUT    | `/transactions/{transaction_id}`   |                                                                     |
| **P4**   | DELETE | `/transactions/{transaction_id}`   |                                                                     |
| **P4**   | GET    | `/movements`                       | TRANSFER alias                                                      |
| **P4**   | GET    | `/movements/{movement_id}`         |                                                                     |
| **P4**   | POST   | `/movements`                       | Creates TRANSFER row                                                |
| **P4**   | PUT    | `/movements/{movement_id}`         | PENDING only                                                        |
| **P4**   | DELETE | `/movements/{movement_id}`         | Cancel PENDING                                                      |
| **P4**   | POST   | `/movements/{movement_id}/execute` | Complete PENDING                                                    |
| **P5**   | GET    | `/reports/spending`                | Service aggregation                                                 |
| **P5**   | GET    | `/reports/cash-flow`               |                                                                     |
| **P5**   | GET    | `/reports/trends`                  |                                                                     |
| **P5**   | GET    | `/reports/export`                  | CSV stub acceptable                                                 |

### Explicitly excluded from MVP

| Method | Path                          | Reason                             |
| ------ | ----------------------------- | ---------------------------------- |
| POST   | `/auth/refresh`               | FR-11 — no refresh token store     |
| POST   | `/auth/logout`                | FR-11 — stateless JWT, no denylist |
| All    | `/budgets/*` (7 routes)       | FR-09 — v4.1 schema                |
| POST   | `/transactions/{id}/split`    | v4 `transaction_splits`            |
| GET    | `/reports/budget-performance` | Depends on budgets                 |

---

## 7. Pydantic schema layer (#25)

Planned package layout under `modules/api/src/papita_txnsapi/`:

```
schemas/
  auth.py          RegisterRequest, LoginForm, TokenResponse, UserResponse
  accounts.py      AccountCreate, AccountUpdate, AccountResponse, BalanceResponse
  categories.py    CategoryCreate, CategoryUpdate, CategoryResponse
  transactions.py  TransactionCreate, TransactionUpdate, TransactionResponse
  movements.py     MovementCreate, MovementUpdate, MovementResponse  (maps to TransactionDTO)
  reports.py       SpendingReport, CashFlowReport, ...
  common.py        PaginatedResponse[T], ErrorDetail
```

**Mapping rules:**

1. API schemas accept API-friendly names (`account_type`, `category_type`); services receive DTOs with v3 names (`account_kind`, `category_kind`).
2. Conversion functions live in `schemas/converters.py` or as `model_validate` adapters on each schema.
3. Response schemas may include computed fields (`balance`, `subcategories`, `is_recurring`) not stored on SQLModel.
4. Never expose `password` hash in responses.

---

## 8. Breaking changes from pre-PPT-031 spec

| Change                                | Migration for API consumers                              |
| ------------------------------------- | -------------------------------------------------------- |
| `full_name` → `username`              | Register/login payloads must include `username`          |
| `account_type` → `account_kind`       | Enum values uppercase in DB; API accepts lowercase slugs |
| `types` / `/types/*` removed          | Use `/categories/*` for income/expense taxonomy          |
| `budget_id` on transactions removed   | Remove from client payloads                              |
| `/movements` backed by `transactions` | `movement_id` = `transaction.id` for TRANSFER rows       |
| `metadata` blob on accounts           | Typed extension fields per `account_kind`                |

---

## 9. Open questions (deferred)

| Item                                             | Gate                                                           | Owner                                                  |
| ------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------ |
| Auth refresh/logout semantics                    | G5 — [`PPT-031-auth-contract.md`](PPT-031-auth-contract.md) §6 | **Written** — deferred 501                             |
| `UsersService.verify_credentials` / `register`   | G5                                                             | **Implemented** in model — wire in #25 routers         |
| `/transaction-templates/*` nested CRUD           | Post-MVP                                                       | #25 follow-up                                          |
| `/account-financing/*` CRUD (asset ↔ loan links) | Post-MVP                                                       | #25 follow-up — v3 table exists, no API routes in MVP  |
| Budget routes: 501 vs unmounted                  | G4 maintainer preference                                       | #28                                                    |
| OpenAPI as sole source of truth                  | After `main.py` ships                                          | #25                                                    |
| `python-multipart` dependency                    | #25 implementation                                             | Add to `modules/api/pyproject.toml` before auth routes |

---

## 10. Requirements traceability

| Requirement                     | Section                                                            | Status     |
| ------------------------------- | ------------------------------------------------------------------ | ---------- |
| FR-07 — API 1:1 model map       | §5                                                                 | ✓          |
| FR-09 — Budgets decision        | §5.5, §6                                                           | ✓ Deferred |
| FR-13 — Category taxonomy       | §4.2, §5.4                                                         | ✓          |
| FR-17 — Single canonical spec   | §2, `API_Endpoints.md.md` + v3 `API_Documentation.md.md`           | ✓          |
| FR-10 — Auth field alignment    | §4.5, §5.2, [`PPT-031-auth-contract.md`](PPT-031-auth-contract.md) | ✓          |
| FR-11 — Refresh/logout deferred | §5.2, auth contract §6                                             | ✓          |
| FR-12 — Reports read model      | §5.8                                                               | ✓          |
| NFR-06 — Mapping doc in docs/   | This file                                                          | ✓          |

---

## References

- v3 schema: [`PPT-031-v1-schema.md`](PPT-031-v1-schema.md)
- v0 audit API gaps: [`PPT-031-v0-audit.md`](PPT-031-v0-audit.md) §10
- v4 budgets: [`PPT-031-v4-extensions.md`](PPT-031-v4-extensions.md) §4
- Supabase platform: [`PPT-031-C-supabase-decision-brief.md`](../issues/PPT-031-C-supabase-decision-brief.md)
- Canonical API spec: [`modules/api/API_Endpoints.md.md`](../../modules/api/API_Endpoints.md.md)
- Design index: [`README.md`](README.md)
