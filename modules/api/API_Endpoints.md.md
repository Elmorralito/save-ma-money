# Save Ma Money - API Endpoints Specification

## 📋 Overview

This document provides a comprehensive specification of all API endpoints for the Save Ma Money budgeting and accounting system.

## 🔗 Base URL

```
Production: https://api.savemamoney.com/api/v1
Development: http://localhost:8000/api/v1
```

## 🔐 Authentication

All endpoints (except health checks and authentication) require a valid JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## 📊 Endpoint Summary

| Resource       | Endpoint          | Methods                |
| -------------- | ----------------- | ---------------------- |
| Health         | `/health`         | GET                    |
| Authentication | `/auth/*`         | POST                   |
| Accounts       | `/accounts/*`     | GET, POST, PUT, DELETE |
| Categories     | `/categories/*`   | GET, POST, PUT, DELETE |
| Budgets        | `/budgets/*`      | GET, POST, PUT, DELETE |
| Transactions   | `/transactions/*` | GET, POST, PUT, DELETE |
| Movements      | `/movements/*`    | GET, POST, PUT, DELETE |
| Reports        | `/reports/*`      | GET                    |

---

## 🏥 Health Check Endpoints

### GET /health

Check API health status.

**Response 200:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-04T15:14:00Z",
  "database": "connected"
}
```

### GET /health/ready

Readiness probe for Kubernetes.

**Response 200:**

```json
{
  "ready": true
}
```

### GET /health/live

Liveness probe for Kubernetes.

**Response 200:**

```json
{
  "alive": true
}
```

---

## 🔑 Authentication Endpoints

### POST /auth/register

Register a new user.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-02-04T15:14:00Z"
}
```

### POST /auth/login

Authenticate user and get access token.

**Request Body (form-data):**

```
username: user@example.com
password: securePassword123
```

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /auth/refresh

Refresh access token.

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /auth/logout

Invalidate current token.

**Response 200:**

```json
{
  "message": "Successfully logged out"
}
```

---

## 🏦 Account Endpoints

### GET /accounts

Retrieve all accounts for the authenticated user.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip (default: 0) |
| limit | integer | No | Maximum records to return (default: 100) |
| account_type | string | No | Filter by account type |
| is_active | boolean | No | Filter by active status |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Main Checking",
      "account_type": "checking",
      "currency": "USD",
      "balance": 5000.0,
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-02-04T15:14:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /accounts/{account_id}

Retrieve a specific account by ID.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| account_id | string (UUID) | Yes | Account identifier |

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Main Checking",
  "account_type": "checking",
  "currency": "USD",
  "balance": 5000.0,
  "is_active": true,
  "metadata": {},
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### POST /accounts

Create a new account.

**Request Body:**

```json
{
  "name": "Savings Account",
  "account_type": "savings",
  "currency": "USD",
  "initial_balance": 1000.0,
  "metadata": {
    "bank": "Example Bank",
    "account_number": "****1234"
  }
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "name": "Savings Account",
  "account_type": "savings",
  "currency": "USD",
  "balance": 1000.0,
  "is_active": true,
  "metadata": {
    "bank": "Example Bank",
    "account_number": "****1234"
  },
  "created_at": "2026-02-04T15:14:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### PUT /accounts/{account_id}

Update an existing account.

**Request Body:**

```json
{
  "name": "Updated Account Name",
  "is_active": true,
  "metadata": {}
}
```

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Updated Account Name",
  "account_type": "savings",
  "currency": "USD",
  "balance": 1000.0,
  "is_active": true,
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### DELETE /accounts/{account_id}

Soft delete an account.

**Response 204:** No Content

### GET /accounts/{account_id}/balance

Get current balance for an account.

**Response 200:**

```json
{
  "account_id": "uuid",
  "balance": 5000.0,
  "currency": "USD",
  "as_of": "2026-02-04T15:14:00Z"
}
```

---

## 📂 Category Endpoints

### GET /categories

Retrieve all categories.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip |
| limit | integer | No | Maximum records to return |
| parent_id | string | No | Filter by parent category |
| category_type | string | No | Filter by type (income/expense) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Food & Dining",
      "category_type": "expense",
      "parent_id": null,
      "icon": "utensils",
      "color": "#FF5733",
      "is_active": true,
      "subcategories": [
        {
          "id": "uuid",
          "name": "Restaurants",
          "category_type": "expense"
        }
      ]
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /categories/{category_id}

Retrieve a specific category.

**Response 200:**

```json
{
  "id": "uuid",
  "name": "Food & Dining",
  "category_type": "expense",
  "parent_id": null,
  "icon": "utensils",
  "color": "#FF5733",
  "is_active": true,
  "budget_allocation": 500.0,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### POST /categories

Create a new category.

**Request Body:**

```json
{
  "name": "Entertainment",
  "category_type": "expense",
  "parent_id": null,
  "icon": "film",
  "color": "#9B59B6"
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "name": "Entertainment",
  "category_type": "expense",
  "parent_id": null,
  "icon": "film",
  "color": "#9B59B6",
  "is_active": true,
  "created_at": "2026-02-04T15:14:00Z"
}
```

### PUT /categories/{category_id}

Update a category.

**Response 200:** Updated category object

### DELETE /categories/{category_id}

Delete a category.

**Response 204:** No Content

---

## 💰 Budget Endpoints

### GET /budgets

Retrieve all budgets.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip |
| limit | integer | No | Maximum records to return |
| period | string | No | Filter by period (monthly/yearly) |
| start_date | date | No | Filter by start date |
| end_date | date | No | Filter by end date |
| status | string | No | Filter by status (active/closed) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "February 2026 Budget",
      "period": "monthly",
      "start_date": "2026-02-01",
      "end_date": "2026-02-28",
      "total_amount": 5000.0,
      "spent_amount": 1250.0,
      "remaining_amount": 3750.0,
      "currency": "USD",
      "status": "active",
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /budgets/{budget_id}

Retrieve a specific budget with details.

**Response 200:**

```json
{
  "id": "uuid",
  "name": "February 2026 Budget",
  "period": "monthly",
  "start_date": "2026-02-01",
  "end_date": "2026-02-28",
  "total_amount": 5000.0,
  "spent_amount": 1250.0,
  "remaining_amount": 3750.0,
  "currency": "USD",
  "status": "active",
  "allocations": [
    {
      "category_id": "uuid",
      "category_name": "Food & Dining",
      "allocated_amount": 500.0,
      "spent_amount": 125.0,
      "remaining_amount": 375.0
    }
  ],
  "created_at": "2026-02-01T00:00:00Z",
  "updated_at": "2026-02-04T15:14:00Z"
}
```

### POST /budgets

Create a new budget.

**Request Body:**

```json
{
  "name": "March 2026 Budget",
  "period": "monthly",
  "start_date": "2026-03-01",
  "end_date": "2026-03-31",
  "total_amount": 5500.0,
  "currency": "USD",
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 600.0
    }
  ]
}
```

**Response 201:** Created budget object

### PUT /budgets/{budget_id}

Update a budget.

**Request Body:**

```json
{
  "name": "Updated Budget Name",
  "total_amount": 6000.0,
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 700.0
    }
  ]
}
```

**Response 200:** Updated budget object

### DELETE /budgets/{budget_id}

Delete a budget.

**Response 204:** No Content

### GET /budgets/{budget_id}/summary

Get budget summary with spending analysis.

**Response 200:**

```json
{
  "budget_id": "uuid",
  "total_budget": 5000.0,
  "total_spent": 1250.0,
  "total_remaining": 3750.0,
  "percentage_used": 25.0,
  "days_remaining": 24,
  "daily_average_spent": 312.5,
  "projected_total_spend": 4375.0,
  "status": "on_track",
  "category_breakdown": [
    {
      "category_id": "uuid",
      "category_name": "Food & Dining",
      "allocated": 500.0,
      "spent": 125.0,
      "percentage_used": 25.0
    }
  ]
}
```

### POST /budgets/{budget_id}/allocations

Add or update budget allocations.

**Request Body:**

```json
{
  "allocations": [
    {
      "category_id": "uuid",
      "allocated_amount": 500.0
    }
  ]
}
```

**Response 200:** Updated allocations

---

## 💳 Transaction Endpoints

### GET /transactions

Retrieve all transactions.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip |
| limit | integer | No | Maximum records to return |
| account_id | string | No | Filter by account |
| category_id | string | No | Filter by category |
| budget_id | string | No | Filter by budget |
| transaction_type | string | No | Filter by type (income/expense/transfer) |
| start_date | date | No | Filter by start date |
| end_date | date | No | Filter by end date |
| min_amount | number | No | Minimum amount filter |
| max_amount | number | No | Maximum amount filter |
| search | string | No | Search in description |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "category_id": "uuid",
      "budget_id": "uuid",
      "transaction_type": "expense",
      "amount": 45.5,
      "currency": "USD",
      "description": "Lunch at restaurant",
      "transaction_date": "2026-02-04",
      "reference_number": "TXN-001",
      "tags": ["food", "dining"],
      "is_recurring": false,
      "created_at": "2026-02-04T12:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /transactions/{transaction_id}

Retrieve a specific transaction.

**Response 200:**

```json
{
  "id": "uuid",
  "account_id": "uuid",
  "account_name": "Main Checking",
  "category_id": "uuid",
  "category_name": "Food & Dining",
  "budget_id": "uuid",
  "transaction_type": "expense",
  "amount": 45.5,
  "currency": "USD",
  "description": "Lunch at restaurant",
  "transaction_date": "2026-02-04",
  "reference_number": "TXN-001",
  "tags": ["food", "dining"],
  "attachments": [],
  "metadata": {},
  "is_recurring": false,
  "recurrence_rule": null,
  "created_at": "2026-02-04T12:30:00Z",
  "updated_at": "2026-02-04T12:30:00Z"
}
```

### POST /transactions

Create a new transaction.

**Request Body:**

```json
{
  "account_id": "uuid",
  "category_id": "uuid",
  "budget_id": "uuid",
  "transaction_type": "expense",
  "amount": 75.0,
  "description": "Grocery shopping",
  "transaction_date": "2026-02-04",
  "tags": ["groceries", "food"],
  "is_recurring": false
}
```

**Response 201:** Created transaction object

### POST /transactions/bulk

Create multiple transactions at once.

**Request Body:**

```json
{
  "transactions": [
    {
      "account_id": "uuid",
      "category_id": "uuid",
      "transaction_type": "expense",
      "amount": 50.0,
      "description": "Transaction 1",
      "transaction_date": "2026-02-04"
    },
    {
      "account_id": "uuid",
      "category_id": "uuid",
      "transaction_type": "expense",
      "amount": 30.0,
      "description": "Transaction 2",
      "transaction_date": "2026-02-04"
    }
  ]
}
```

**Response 201:**

```json
{
  "created": 2,
  "failed": 0,
  "transactions": [...]
}
```

### PUT /transactions/{transaction_id}

Update a transaction.

**Response 200:** Updated transaction object

### DELETE /transactions/{transaction_id}

Delete a transaction.

**Response 204:** No Content

### POST /transactions/{transaction_id}/split

Split a transaction into multiple parts.

**Request Body:**

```json
{
  "splits": [
    {
      "category_id": "uuid",
      "amount": 30.0,
      "description": "Part 1"
    },
    {
      "category_id": "uuid",
      "amount": 20.0,
      "description": "Part 2"
    }
  ]
}
```

**Response 200:** Split transaction details

---

## 🔄 Movement Endpoints

### GET /movements

Retrieve all movements (transfers between accounts).

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip |
| limit | integer | No | Maximum records to return |
| source_account_id | string | No | Filter by source account |
| destination_account_id | string | No | Filter by destination account |
| status | string | No | Filter by status |
| start_date | date | No | Filter by start date |
| end_date | date | No | Filter by end date |

**Response 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "source_account_id": "uuid",
      "source_account_name": "Checking",
      "destination_account_id": "uuid",
      "destination_account_name": "Savings",
      "amount": 500.0,
      "currency": "USD",
      "status": "completed",
      "description": "Monthly savings transfer",
      "movement_date": "2026-02-01",
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

### GET /movements/{movement_id}

Retrieve a specific movement.

**Response 200:** Movement object with full details

### POST /movements

Create a new movement (transfer).

**Request Body:**

```json
{
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "amount": 1000.0,
  "description": "Transfer to savings",
  "movement_date": "2026-02-04",
  "scheduled": false
}
```

**Response 201:** Created movement object

### PUT /movements/{movement_id}

Update a pending movement.

**Response 200:** Updated movement object

### DELETE /movements/{movement_id}

Cancel a pending movement.

**Response 204:** No Content

### POST /movements/{movement_id}/execute

Execute a scheduled movement.

**Response 200:**

```json
{
  "id": "uuid",
  "status": "completed",
  "executed_at": "2026-02-04T15:14:00Z"
}
```

---

## 📈 Report Endpoints

### GET /reports/spending

Get spending report.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_date | date | Yes | Report start date |
| end_date | date | Yes | Report end date |
| group_by | string | No | Group by (category/account/day/week/month) |
| account_id | string | No | Filter by account |

**Response 200:**

```json
{
  "period": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  },
  "total_spending": 2500.0,
  "total_income": 5000.0,
  "net_savings": 2500.0,
  "breakdown": [
    {
      "category": "Food & Dining",
      "amount": 450.0,
      "percentage": 18.0,
      "transaction_count": 15
    }
  ],
  "trend": [
    {
      "date": "2026-02-01",
      "spending": 100.0,
      "income": 0.0
    }
  ]
}
```

### GET /reports/budget-performance

Get budget performance report.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| budget_id | string | No | Specific budget ID |
| period | string | No | Period (monthly/quarterly/yearly) |

**Response 200:**

```json
{
  "budgets": [
    {
      "budget_id": "uuid",
      "budget_name": "February 2026",
      "total_budget": 5000.0,
      "total_spent": 2500.0,
      "variance": 2500.0,
      "performance_score": 85,
      "categories": [
        {
          "category_name": "Food & Dining",
          "budgeted": 500.0,
          "actual": 450.0,
          "variance": 50.0,
          "status": "under_budget"
        }
      ]
    }
  ]
}
```

### GET /reports/cash-flow

Get cash flow report.

**Response 200:**

```json
{
  "period": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  },
  "opening_balance": 10000.0,
  "closing_balance": 12500.0,
  "total_inflows": 5000.0,
  "total_outflows": 2500.0,
  "net_cash_flow": 2500.0,
  "by_account": [
    {
      "account_id": "uuid",
      "account_name": "Checking",
      "inflows": 5000.0,
      "outflows": 2000.0,
      "net": 3000.0
    }
  ]
}
```

### GET /reports/trends

Get spending trends analysis.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| months | integer | No | Number of months to analyze (default: 6) |
| category_id | string | No | Filter by category |

**Response 200:**

```json
{
  "analysis_period": {
    "start": "2025-09-01",
    "end": "2026-02-28"
  },
  "monthly_trends": [
    {
      "month": "2026-02",
      "total_spending": 2500.0,
      "total_income": 5000.0,
      "savings_rate": 50.0
    }
  ],
  "category_trends": [
    {
      "category": "Food & Dining",
      "average_monthly": 450.0,
      "trend": "stable",
      "change_percentage": 2.5
    }
  ],
  "insights": [
    {
      "type": "warning",
      "message": "Entertainment spending increased 25% this month"
    }
  ]
}
```

### GET /reports/export

Export report data.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| report_type | string | Yes | Type of report |
| format | string | Yes | Export format (csv/xlsx/pdf) |
| start_date | date | Yes | Start date |
| end_date | date | Yes | End date |

**Response 200:** File download

---

## ❌ Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "amount",
      "message": "Amount must be positive"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found",
  "resource_type": "Transaction",
  "resource_id": "uuid"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "amount"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

---

## 📝 Rate Limiting

| Tier       | Requests/Minute | Requests/Day |
| ---------- | --------------- | ------------ |
| Free       | 60              | 1,000        |
| Pro        | 300             | 10,000       |
| Enterprise | Unlimited       | Unlimited    |

Rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1707058440
```
