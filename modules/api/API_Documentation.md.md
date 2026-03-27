# Save Ma Money - API Documentation

## 📖 Introduction

Welcome to the Save Ma Money API documentation. This comprehensive guide provides all the information needed to integrate with our budgeting and accounting system.

### API Version

- **Current Version:** v1
- **Base URL:** `https://api.savemamoney.com/api/v1`
- **OpenAPI Spec:** `https://api.savemamoney.com/api/openapi.json`

### Key Features

- RESTful API design
- JSON request/response format
- JWT-based authentication
- Comprehensive error handling
- Rate limiting
- Pagination support
- Filtering and sorting capabilities

---

## 🔐 Authentication

### Overview

The Save Ma Money API uses JWT (JSON Web Tokens) for authentication. All API requests (except public endpoints) must include a valid access token.

### Obtaining an Access Token

```bash
curl -X POST "https://api.savemamoney.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Using the Access Token

Include the token in the `Authorization` header:

```bash
curl -X GET "https://api.savemamoney.com/api/v1/accounts" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Refresh

Before the token expires, refresh it:

```bash
curl -X POST "https://api.savemamoney.com/api/v1/auth/refresh" \
  -H "Authorization: Bearer <current_token>"
```

### Security Best Practices

1. **Never expose tokens** in URLs or logs
2. **Store tokens securely** (HttpOnly cookies or secure storage)
3. **Implement token refresh** before expiration
4. **Use HTTPS** for all API calls

---

## 📋 Request/Response Format

### Request Headers

| Header          | Required | Description                           |
| --------------- | -------- | ------------------------------------- |
| `Authorization` | Yes\*    | Bearer token for authentication       |
| `Content-Type`  | Yes      | `application/json` for JSON bodies    |
| `Accept`        | No       | `application/json` (default)          |
| `X-Request-ID`  | No       | Custom request identifier for tracing |

\*Not required for public endpoints

### Request Body Format

All request bodies should be valid JSON:

```json
{
  "field_name": "value",
  "nested_object": {
    "nested_field": "nested_value"
  },
  "array_field": ["item1", "item2"]
}
```

### Response Format

#### Success Response

```json
{
  "id": "uuid",
  "field": "value",
  "created_at": "2026-02-04T15:14:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

#### List Response (Paginated)

```json
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 20,
  "has_more": true
}
```

#### Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "request_id": "uuid",
  "timestamp": "2026-02-04T15:14:00Z"
}
```

---

## 📄 Pagination

### Query Parameters

| Parameter | Type    | Default | Max | Description               |
| --------- | ------- | ------- | --- | ------------------------- |
| `skip`    | integer | 0       | -   | Number of records to skip |
| `limit`   | integer | 20      | 100 | Maximum records to return |

### Example

```bash
GET /api/v1/transactions?skip=20&limit=10
```

### Response Headers

```
X-Total-Count: 150
X-Page-Size: 10
X-Current-Page: 3
```

---

## 🔍 Filtering & Sorting

### Filtering

Use query parameters to filter results:

```bash
# Single filter
GET /api/v1/transactions?category_id=uuid

# Multiple filters
GET /api/v1/transactions?category_id=uuid&transaction_type=expense

# Date range
GET /api/v1/transactions?start_date=2026-02-01&end_date=2026-02-28

# Amount range
GET /api/v1/transactions?min_amount=100&max_amount=500
```

### Sorting

Use `sort_by` and `sort_order` parameters:

```bash
# Sort by date descending
GET /api/v1/transactions?sort_by=transaction_date&sort_order=desc

# Sort by amount ascending
GET /api/v1/transactions?sort_by=amount&sort_order=asc
```

### Search

Use the `search` parameter for text search:

```bash
GET /api/v1/transactions?search=grocery
```

---

## 📊 Data Models

### Account Model

```python
class Account:
    id: UUID                    # Unique identifier
    name: str                   # Account name
    account_type: AccountType   # checking, savings, credit, cash
    currency: str               # ISO 4217 currency code
    balance: Decimal            # Current balance
    is_active: bool             # Active status
    metadata: dict              # Additional metadata
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### Category Model

```python
class Category:
    id: UUID                    # Unique identifier
    name: str                   # Category name
    category_type: CategoryType # income, expense
    parent_id: Optional[UUID]   # Parent category (for subcategories)
    icon: str                   # Icon identifier
    color: str                  # Hex color code
    is_active: bool             # Active status
    created_at: datetime        # Creation timestamp
```

### Budget Model

```python
class Budget:
    id: UUID                    # Unique identifier
    name: str                   # Budget name
    period: BudgetPeriod        # monthly, quarterly, yearly
    start_date: date            # Budget start date
    end_date: date              # Budget end date
    total_amount: Decimal       # Total budget amount
    currency: str               # ISO 4217 currency code
    status: BudgetStatus        # active, closed, archived
    allocations: List[Allocation]  # Category allocations
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### Transaction Model

```python
class Transaction:
    id: UUID                    # Unique identifier
    account_id: UUID            # Associated account
    category_id: UUID           # Associated category
    budget_id: Optional[UUID]   # Associated budget
    transaction_type: TransactionType  # income, expense, transfer
    amount: Decimal             # Transaction amount
    currency: str               # ISO 4217 currency code
    description: str            # Transaction description
    transaction_date: date      # Transaction date
    reference_number: str       # External reference
    tags: List[str]             # Transaction tags
    is_recurring: bool          # Recurring transaction flag
    recurrence_rule: Optional[str]  # RRULE for recurring
    metadata: dict              # Additional metadata
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### Movement Model

```python
class Movement:
    id: UUID                    # Unique identifier
    source_account_id: UUID     # Source account
    destination_account_id: UUID  # Destination account
    amount: Decimal             # Transfer amount
    currency: str               # ISO 4217 currency code
    status: MovementStatus      # pending, completed, cancelled
    description: str            # Movement description
    movement_date: date         # Movement date
    scheduled_date: Optional[date]  # Scheduled execution date
    executed_at: Optional[datetime]  # Actual execution time
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

---

## 🔄 Webhooks (Future)

### Supported Events

| Event                      | Description               |
| -------------------------- | ------------------------- |
| `transaction.created`      | New transaction created   |
| `transaction.updated`      | Transaction modified      |
| `budget.threshold_reached` | Budget threshold exceeded |
| `movement.completed`       | Transfer completed        |

### Webhook Payload

```json
{
  "event": "transaction.created",
  "timestamp": "2026-02-04T15:14:00Z",
  "data": {
    "id": "uuid",
    "type": "transaction",
    "attributes": {...}
  }
}
```

---

## 🛠️ SDK Examples

### Python

```python
import httpx
from typing import Optional

class SaveMaMoneyClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    async def get_transactions(
        self,
        skip: int = 0,
        limit: int = 20,
        category_id: Optional[str] = None
    ):
        params = {"skip": skip, "limit": limit}
        if category_id:
            params["category_id"] = category_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transactions",
                headers=self.headers,
                params=params
            )
            return response.json()

    async def create_transaction(self, transaction_data: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transactions",
                headers=self.headers,
                json=transaction_data
            )
            return response.json()

# Usage
client = SaveMaMoneyClient(
    base_url="https://api.savemamoney.com/api/v1",
    api_key="your_access_token"
)

# Get transactions
transactions = await client.get_transactions(limit=10)

# Create transaction
new_transaction = await client.create_transaction({
    "account_id": "uuid",
    "category_id": "uuid",
    "transaction_type": "expense",
    "amount": 50.00,
    "description": "Coffee",
    "transaction_date": "2026-02-04"
})
```

### JavaScript/TypeScript

```typescript
interface Transaction {
  id: string;
  account_id: string;
  category_id: string;
  transaction_type: "income" | "expense" | "transfer";
  amount: number;
  description: string;
  transaction_date: string;
}

class SaveMaMoneyClient {
  private baseUrl: string;
  private headers: HeadersInit;

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  async getTransactions(params?: {
    skip?: number;
    limit?: number;
    category_id?: string;
  }): Promise<{ items: Transaction[]; total: number }> {
    const queryString = new URLSearchParams(
      params as Record<string, string>,
    ).toString();

    const response = await fetch(
      `${this.baseUrl}/transactions?${queryString}`,
      { headers: this.headers },
    );

    return response.json();
  }

  async createTransaction(data: Omit<Transaction, "id">): Promise<Transaction> {
    const response = await fetch(`${this.baseUrl}/transactions`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(data),
    });

    return response.json();
  }
}

// Usage
const client = new SaveMaMoneyClient(
  "https://api.savemamoney.com/api/v1",
  "your_access_token",
);

const transactions = await client.getTransactions({ limit: 10 });
```

### cURL Examples

```bash
# Get all accounts
curl -X GET "https://api.savemamoney.com/api/v1/accounts" \
  -H "Authorization: Bearer $TOKEN"

# Create a transaction
curl -X POST "https://api.savemamoney.com/api/v1/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "uuid",
    "category_id": "uuid",
    "transaction_type": "expense",
    "amount": 50.00,
    "description": "Grocery shopping",
    "transaction_date": "2026-02-04"
  }'

# Get budget summary
curl -X GET "https://api.savemamoney.com/api/v1/budgets/uuid/summary" \
  -H "Authorization: Bearer $TOKEN"

# Export report
curl -X GET "https://api.savemamoney.com/api/v1/reports/export?report_type=spending&format=csv&start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer $TOKEN" \
  -o spending_report.csv
```

---

## ⚠️ Error Handling

### Error Codes

| Code                   | HTTP Status | Description               |
| ---------------------- | ----------- | ------------------------- |
| `VALIDATION_ERROR`     | 422         | Request validation failed |
| `AUTHENTICATION_ERROR` | 401         | Invalid or expired token  |
| `AUTHORIZATION_ERROR`  | 403         | Insufficient permissions  |
| `NOT_FOUND`            | 404         | Resource not found        |
| `CONFLICT`             | 409         | Resource conflict         |
| `RATE_LIMIT_EXCEEDED`  | 429         | Too many requests         |
| `INTERNAL_ERROR`       | 500         | Server error              |

### Error Response Structure

```json
{
  "detail": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "amount",
      "message": "Amount must be a positive number",
      "code": "positive_number"
    }
  ],
  "request_id": "req_abc123",
  "timestamp": "2026-02-04T15:14:00Z",
  "documentation_url": "https://docs.savemamoney.com/errors/VALIDATION_ERROR"
}
```

### Handling Errors

```python
import httpx

async def safe_api_call():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.savemamoney.com/api/v1/transactions"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            # Handle authentication error
            await refresh_token()
        elif e.response.status_code == 429:
            # Handle rate limiting
            retry_after = e.response.headers.get("Retry-After", 60)
            await asyncio.sleep(int(retry_after))
        else:
            #
```
