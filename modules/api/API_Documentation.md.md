# Save Ma Money — API Integration Guide

> **FR-17:** Endpoint contracts (paths, query params, request/response bodies) live in the **canonical spec**
> [`API_Endpoints.md.md`](API_Endpoints.md.md). This guide covers integration patterns only — do not treat it as a second source of truth for field names.
>
> **v3 mapping:** [`docs/design/PPT-031-api-model-mapping.md`](../../docs/design/PPT-031-api-model-mapping.md) · **Auth:** [`docs/design/PPT-031-auth-contract.md`](../../docs/design/PPT-031-auth-contract.md)

## Introduction

REST API for personal finance: accounts, categories, transactions, transfers (movements), and reports. JSON over HTTPS; JWT bearer auth for protected routes.

| Topic                   | Value                                     |
| ----------------------- | ----------------------------------------- |
| API version             | v1                                        |
| Base URL                | `https://api.savemamoney.com/api/v1`      |
| OpenAPI (when deployed) | `/api/openapi.json`                       |
| Database platform       | PostgreSQL (`papita_transactions` schema) |

### MVP scope

| In MVP                                        | Deferred (501)                               |
| --------------------------------------------- | -------------------------------------------- |
| Health, register, login                       | `/auth/refresh`, `/auth/logout`              |
| Accounts, categories, transactions, movements | All `/budgets/*`                             |
| Reports (except budget-performance)           | Transaction split, budget-performance report |

---

## Authentication

Local JWT (HS256) backed by `papita_transactions.users`. See [`PPT-031-auth-contract.md`](../../docs/design/PPT-031-auth-contract.md).

### Register

```bash
curl -X POST "https://api.savemamoney.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "user@example.local",
    "password": "SecurePass1!"
  }'
```

Returns **201** with `id`, `username`, `email`, `created_at` — **no token**. Client must log in separately.

### Login

```bash
curl -X POST "https://api.savemamoney.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.local&password=SecurePass1!"
```

The form field `username` accepts **email or username**.

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the token

```bash
curl -X GET "https://api.savemamoney.com/api/v1/accounts" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

JWT `sub` claim = `str(users.id)`. All financial data is scoped to that tenant.

### Refresh and logout (not in MVP)

`/auth/refresh` and `/auth/logout` return **501**. On 401, re-authenticate via `/auth/login`. Discard the token client-side when the user signs out.

### Security practices

1. Use **HTTPS** only.
2. Do not log tokens or passwords.
3. Store tokens in memory or secure storage (not localStorage if XSS is a concern).
4. Re-login when `expires_in` elapses (default 3600 s).

---

## Request and response conventions

### Headers

| Header          | Required           | Description                                                       |
| --------------- | ------------------ | ----------------------------------------------------------------- |
| `Authorization` | Protected routes   | `Bearer <access_token>`                                           |
| `Content-Type`  | POST/PUT with body | `application/json` or `application/x-www-form-urlencoded` (login) |
| `Accept`        | No                 | `application/json` (default)                                      |

### Pagination

Query params: `skip` (default 0), `limit` (default 100 on most list endpoints).

```json
{
  "items": [],
  "total": 42,
  "skip": 0,
  "limit": 20
}
```

### Filtering (transactions example)

Supported filters match [`API_Endpoints.md.md`](API_Endpoints.md.md) — do not assume undeclared params (e.g. no `sort_by` in MVP).

```bash
GET /api/v1/transactions?category_id=uuid&transaction_type=expense&status=completed
GET /api/v1/transactions?start_date=2026-02-01&end_date=2026-02-28&account_id=uuid
```

Default transaction list **excludes** `transfer` rows; use `/movements` or `?transaction_type=transfer`.

### Enum convention

API JSON uses **lowercase** slugs (`expense`, `completed`, `checking`). PostgreSQL stores **uppercase** enums (`EXPENSE`, `COMPLETED`, `CHECKING`).

---

## v3 data shapes (integration reference)

These match the v3 target schema. `balance` is read from the `account_balances` materialized view, not stored on `accounts`.

### Account

```python
{
  "id": "uuid",
  "name": "Main Checking",
  "account_kind": "checking",       # → accounts.account_kind
  "ledger_side": "asset",             # asset | liability
  "currency": "USD",
  "balance": 5000.0,                  # from account_balances view
  "initial_value": 1000.0,            # write as initial_value on create
  "is_active": true,
  "opened_at": "2026-01-01T00:00:00Z",
  "banking_details": {                # when account_kind uses banking extension
    "entity": "Example Bank",
    "account_number": "****1234"
  },
  "created_at": "...",
  "updated_at": "..."
}
```

**Removed from v3 MVP:** `account_type`, `metadata`, `initial_balance`.

### Category

```python
{
  "id": "uuid",
  "name": "Food & Dining",
  "category_type": "expense",         # API alias → category_kind (INCOME|EXPENSE)
  "parent_id": null,
  "icon": "utensils",
  "color": "#FF5733",
  "is_active": true,
  "subcategories": []                 # computed from parent_id, not stored
}
```

**Removed:** `budget_allocation` (budgets deferred).

### Transaction (income / expense)

```python
{
  "id": "uuid",
  "account_id": "uuid",               # derived: to_account (income) or from_account (expense)
  "category_id": "uuid",
  "transaction_type": "expense",      # → transaction_kind
  "status": "completed",              # pending | completed | cancelled
  "amount": 45.5,
  "currency": "USD",
  "description": "Lunch",
  "transaction_date": "2026-02-04",   # → transaction_ts
  "reference_number": "TXN-001",
  "tags": ["food"],
  "is_recurring": false,                # template_id IS NOT NULL
  "template_id": null
}
```

**Removed from MVP:** `budget_id`, `attachments`, `metadata`, `recurrence_rule`.

### Movement (transfer alias)

Same row as `transactions` with `transaction_kind = TRANSFER`.

```python
{
  "id": "uuid",
  "source_account_id": "uuid",        # → from_account_id
  "destination_account_id": "uuid",   # → to_account_id
  "amount": 500.0,
  "currency": "USD",                  # must match both accounts
  "status": "completed",
  "description": "Savings transfer",
  "movement_date": "2026-02-01"
}
```

### User (register response)

```python
{
  "id": "uuid",
  "username": "johndoe",
  "email": "user@example.local",
  "created_at": "..."
}
```

**Removed:** `full_name`. Password never returned.

### Budget

**Not in MVP** — endpoints return 501. Future design: [`PPT-031-v4-extensions.md`](../../docs/design/PPT-031-v4-extensions.md) §4.

---

## SDK examples (v3)

### Python

```python
import httpx

BASE = "https://api.savemamoney.com/api/v1"


async def register_and_login() -> str:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BASE}/auth/register",
            json={
                "username": "johndoe",
                "email": "user@example.local",
                "password": "SecurePass1!",
            },
        )
        login = await client.post(
            f"{BASE}/auth/login",
            data={"username": "user@example.local", "password": "SecurePass1!"},
        )
        login.raise_for_status()
        return login.json()["access_token"]


async def create_expense(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "account_id": "account-uuid",
        "category_id": "category-uuid",
        "transaction_type": "expense",
        "amount": 50.0,
        "currency": "USD",
        "description": "Coffee",
        "transaction_date": "2026-02-04",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE}/transactions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
```

### TypeScript

```typescript
interface TransactionCreate {
  account_id: string;
  category_id: string;
  transaction_type: "income" | "expense";
  amount: number;
  currency: string;
  description: string;
  transaction_date: string;
}

async function login(
  baseUrl: string,
  identifier: string,
  password: string,
): Promise<string> {
  const body = new URLSearchParams({ username: identifier, password });
  const res = await fetch(`${baseUrl}/auth/login`, { method: "POST", body });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.access_token;
}
```

### cURL

```bash
# Create account
curl -X POST "$BASE/accounts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Checking",
    "account_kind": "checking",
    "currency": "USD",
    "initial_value": 1000.0
  }'

# Transfer between accounts (movements alias)
curl -X POST "$BASE/movements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_account_id": "from-uuid",
    "destination_account_id": "to-uuid",
    "amount": 500.0,
    "currency": "USD",
    "movement_date": "2026-02-04"
  }'

# Spending report (COMPLETED expenses only — see API_Endpoints)
curl -X GET "$BASE/reports/spending?start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Error handling

| HTTP | Typical cause                                           |
| ---- | ------------------------------------------------------- |
| 401  | Invalid/expired JWT or bad login                        |
| 403  | Insufficient permissions                                |
| 404  | Resource not found (including other tenant's IDs)       |
| 409  | Duplicate username/email on register                    |
| 422  | Validation error (DTO / Pydantic)                       |
| 501  | Deferred MVP endpoint (budgets, refresh, logout, split) |

```json
{
  "detail": "Incorrect username or password"
}
```

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be 8-128 characters long...",
      "type": "value_error"
    }
  ]
}
```

On **401**, obtain a new token via `/auth/login` — there is no refresh endpoint in MVP.

---

## Webhooks (future)

Not implemented. Planned events may include `transaction.created`, `movement.completed`. Budget webhooks depend on v4 budget schema.

---

## Further reading

| Document                                                                         | Purpose                          |
| -------------------------------------------------------------------------------- | -------------------------------- |
| [`API_Endpoints.md.md`](API_Endpoints.md.md)                                     | Canonical endpoint specification |
| [`PPT-031-api-model-mapping.md`](../../docs/design/PPT-031-api-model-mapping.md) | Endpoint → DTO → SQLModel        |
| [`PPT-031-auth-contract.md`](../../docs/design/PPT-031-auth-contract.md)         | Auth strategy and JWT rules      |
| [`PPT-031-v1-schema.md`](../../docs/design/PPT-031-v1-schema.md)                 | v3 database schema               |
