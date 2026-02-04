# Save Ma Money - FastAPI Backend Service

## 📋 Overview

A comprehensive budgeting and accounting system built with FastAPI, designed to manage company budgets, expenses, and financial movements. This service provides RESTful APIs for transaction management, budget tracking, and financial reporting.

## 🏗️ Project Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│              (Web App / Mobile App / External Services)          │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway / Load Balancer                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application Layer                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │  Routers  │──│ Handlers  │──│   Deps    │──│  Schemas  │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Access Layer                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              papita_txnsmodel Library                    │   │
│  │  (Models, Repositories, Services, Business Logic)        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Database Layer                               │
│              (PostgreSQL / SQLite / MongoDB)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer                | Responsibility                                                              |
| -------------------- | --------------------------------------------------------------------------- |
| **Routers**          | HTTP endpoint definitions, request/response handling, OpenAPI documentation |
| **Handlers**         | Business logic orchestration, data transformation, validation rules         |
| **Dependencies**     | Dependency injection, session management, authentication, authorization     |
| **Schemas**          | Pydantic models for request/response validation and serialization           |
| **papita_txnsmodel** | Core domain models, repositories, services, and data access logic           |

## 📁 Project Structure

```
save-ma-money/
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Application settings & configuration
│   │   └── logging.py             # Logging configuration
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py            # Authentication & authorization utilities
│   │   ├── exceptions.py          # Custom exception definitions
│   │   └── middleware.py          # Custom middleware (logging, timing, etc.)
│   │
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── database.py            # Database session dependency
│   │   ├── auth.py                # Authentication dependencies
│   │   ├── pagination.py          # Pagination parameters dependency
│   │   ├── transaction_deps.py    # Transaction-specific dependencies
│   │   ├── budget_deps.py         # Budget-specific dependencies
│   │   ├── account_deps.py        # Account-specific dependencies
│   │   ├── category_deps.py       # Category-specific dependencies
│   │   ├── movement_deps.py       # Movement-specific dependencies
│   │   └── report_deps.py         # Report-specific dependencies
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py                # Base handler with common operations
│   │   ├── transaction_handler.py # Transaction business logic
│   │   ├── budget_handler.py      # Budget business logic
│   │   ├── account_handler.py     # Account business logic
│   │   ├── category_handler.py    # Category business logic
│   │   ├── movement_handler.py    # Movement business logic
│   │   └── report_handler.py      # Report generation logic
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py              # Common/shared schemas (pagination, responses)
│   │   ├── auth.py                # Authentication schemas
│   │   ├── transaction.py         # Transaction request/response schemas
│   │   ├── budget.py              # Budget request/response schemas
│   │   ├── account.py             # Account request/response schemas
│   │   ├── category.py            # Category request/response schemas
│   │   ├── movement.py            # Movement request/response schemas
│   │   └── report.py              # Report request/response schemas
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── router.py              # Main router aggregator
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py          # Health check endpoints
│   │       ├── auth.py            # Authentication endpoints
│   │       ├── transactions.py    # Transaction endpoints
│   │       ├── budgets.py         # Budget endpoints
│   │       ├── accounts.py        # Account endpoints
│   │       ├── categories.py      # Category endpoints
│   │       ├── movements.py       # Movement endpoints
│   │       └── reports.py         # Report endpoints
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py          # Custom validators
│   │   ├── formatters.py          # Data formatters
│   │   └── helpers.py             # Helper functions
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py            # Pytest fixtures
│       ├── unit/
│       │   ├── test_handlers/
│       │   └── test_dependencies/
│       ├── integration/
│       │   └── test_routers/
│       └── e2e/
│           └── test_api_flows/
│
├── modules/
│   └── model/                     # papita_txnsmodel library
│       └── src/
│           └── papita_txnsmodel/
│               ├── models/        # Domain models
│               ├── repositories/  # Data access layer
│               ├── services/      # Business services
│               └── ...
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/
│   ├── start.sh
│   └── migrate.sh
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── alembic.ini
└── README.md
```

## 🔧 Core Components

### 1. Configuration Management (`api/config/`)

```python
# settings.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Save Ma Money API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 2. Dependencies Layer (`api/dependencies/`)

The dependencies layer provides dependency injection for routers and handlers, managing:

- Database sessions
- Authentication/Authorization
- Service instantiation from papita_txnsmodel
- Common query parameters

```python
# database.py
from typing import Generator
from sqlalchemy.orm import Session
from papita_txnsmodel import get_session_factory

def get_db() -> Generator[Session, None, None]:
    """Provides database session dependency."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from api.config.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings)
):
    """Validates JWT token and returns current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id

async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """Ensures user is active."""
    # Additional validation logic
    return current_user
```

```python
# pagination.py
from fastapi import Query
from dataclasses import dataclass

@dataclass
class PaginationParams:
    skip: int
    limit: int

def get_pagination(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return")
) -> PaginationParams:
    """Provides pagination parameters dependency."""
    return PaginationParams(skip=skip, limit=limit)
```

```python
# transaction_deps.py
from fastapi import Depends
from sqlalchemy.orm import Session
from papita_txnsmodel import TransactionService, TransactionRepository

from api.dependencies.database import get_db

def get_transaction_repository(
    db: Session = Depends(get_db)
) -> TransactionRepository:
    """Provides TransactionRepository instance."""
    return TransactionRepository(db)

def get_transaction_service(
    repository: TransactionRepository = Depends(get_transaction_repository)
) -> TransactionService:
    """Provides TransactionService instance."""
    return TransactionService(repository)
```

```python
# budget_deps.py
from fastapi import Depends
from sqlalchemy.orm import Session
from papita_txnsmodel import BudgetService, BudgetRepository

from api.dependencies.database import get_db

def get_budget_repository(
    db: Session = Depends(get_db)
) -> BudgetRepository:
    """Provides BudgetRepository instance."""
    return BudgetRepository(db)

def get_budget_service(
    repository: BudgetRepository = Depends(get_budget_repository)
) -> BudgetService:
    """Provides BudgetService instance."""
    return BudgetService(repository)
```

### 3. Handlers Layer (`api/handlers/`)

The handlers layer contains business logic that orchestrates calls to papita_txnsmodel services and transforms data between API schemas and domain models.

```python
# base.py
from typing import TypeVar, Generic, List, Optional
from api.schemas.common import PaginatedResponse

T = TypeVar("T")
S = TypeVar("S")

class BaseHandler(Generic[T, S]):
    """Base handler with common CRUD operations."""

    def __init__(self, service: S):
        self.service = service

    async def get_paginated(
        self,
        skip: int,
        limit: int,
        **filters
    ) -> PaginatedResponse[T]:
        """Get paginated results with filters."""
        items = await self.service.get_all(skip=skip, limit=limit, **filters)
        total = await self.service.count(**filters)
        return PaginatedResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total
        )
```

```python
# transaction_handler.py
from typing import List, Optional
from datetime import date
from decimal import Decimal

from papita_txnsmodel import TransactionService, Transaction
from api.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilter,
    BulkTransactionCreate,
    BulkTransactionResponse,
    SplitTransactionRequest
)
from api.schemas.common import PaginatedResponse
from api.handlers.base import BaseHandler

class TransactionHandler(BaseHandler[TransactionResponse, TransactionService]):
    """Handler for transaction business logic."""

    def __init__(self, service: TransactionService):
        super().__init__(service)

    async def create_transaction(
        self,
        user_id: str,
        data: TransactionCreate
    ) -> TransactionResponse:
        """Create a new transaction."""
        transaction = await self.service.create(
            user_id=user_id,
            **data.model_dump()
        )
        return TransactionResponse.model_validate(transaction)

    async def get_transactions(
        self,
        user_id: str,
        skip: int,
        limit: int,
        filters: TransactionFilter
    ) -> PaginatedResponse[TransactionResponse]:
        """Get filtered and paginated transactions."""
        filter_dict = filters.model_dump(exclude_none=True)
        return await self.get_paginated(
            skip=skip,
            limit=limit,
            user_id=user_id,
            **filter_dict
        )

    async def get_transaction_by_id(
        self,
        user_id: str,
        transaction_id: str
    ) -> Optional[TransactionResponse]:
        """Get a single transaction by ID."""
        transaction = await self.service.get_by_id(
            transaction_id,
            user_id=user_id
        )
        if transaction:
            return TransactionResponse.model_validate(transaction)
        return None

    async def update_transaction(
        self,
        user_id: str,
        transaction_id: str,
        data: TransactionUpdate
    ) -> Optional[TransactionResponse]:
        """Update an existing transaction."""
        transaction = await self.service.update(
            transaction_id,
            user_id=user_id,
            **data.model_dump(exclude_unset=True)
        )
        if transaction:
            return TransactionResponse.model_validate(transaction)
        return None

    async def delete_transaction(
        self,
        user_id: str,
        transaction_id: str
    ) -> bool:
        """Delete a transaction."""
        return await self.service.delete(transaction_id, user_id=user_id)

    async def bulk_create_transactions(
        self,
        user_id: str,
        data: BulkTransactionCreate
    ) -> BulkTransactionResponse:
        """Create multiple transactions at once."""
        created = []
        failed = []

        for txn_data in data.transactions:
            try:
                transaction = await self.service.create(
                    user_id=user_id,
                    **txn_data.model_dump()
                )
                created.append(TransactionResponse.model_validate(transaction))
            except Exception as e:
                failed.append({"data": txn_data, "error": str(e)})

        return BulkTransactionResponse(
            created=len(created),
            failed=len(failed),
            transactions=created,
            errors=failed
        )

    async def split_transaction(
        self,
        user_id: str,
        transaction_id: str,
        data: SplitTransactionRequest
    ) -> List[TransactionResponse]:
        """Split a transaction into multiple parts."""
        transactions = await self.service.split_transaction(
            transaction_id,
            user_id=user_id,
            splits=data.splits
        )
        return [TransactionResponse.model_validate(t) for t in transactions]
```

```python
# budget_handler.py
from typing import List, Optional
from datetime import date
from decimal import Decimal

from papita_txnsmodel import BudgetService, Budget
from api.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummary,
    BudgetAllocationRequest
)
from api.schemas.common import PaginatedResponse
from api.handlers.base import BaseHandler

class BudgetHandler(BaseHandler[BudgetResponse, BudgetService]):
    """Handler for budget business logic."""

    def __init__(self, service: BudgetService):
        super().__init__(service)

    async def create_budget(
        self,
        user_id: str,
        data: BudgetCreate
    ) -> BudgetResponse:
        """Create a new budget with allocations."""
        budget = await self.service.create(
            user_id=user_id,
            **data.model_dump()
        )
        return BudgetResponse.model_validate(budget)

    async def get_budgets(
        self,
        user_id: str,
        skip: int,
        limit: int,
        period: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> PaginatedResponse[BudgetResponse]:
        """Get filtered and paginated budgets."""
        return await self.get_paginated(
            skip=skip,
            limit=limit,
            user_id=user_id,
            period=period,
            status=status,
            start_date=start_date,
            end_date=end_date
        )

    async def get_budget_by_id(
        self,
        user_id: str,
        budget_id: str
    ) -> Optional[BudgetResponse]:
        """Get a single budget by ID with allocations."""
        budget = await self.service.get_by_id(budget_id, user_id=user_id)
        if budget:
            return BudgetResponse.model_validate(budget)
        return None

    async def get_budget_summary(
        self,
        user_id: str,
        budget_id: str
    ) -> Optional[BudgetSummary]:
        """Get budget summary with spending analysis."""
        budget = await self.service.get_by_id(budget_id, user_id=user_id)
        if not budget:
            return None

        # Calculate summary metrics
        spent = await self.service.calculate_spent(budget_id)
        remaining = budget.total_amount - spent
        percentage_used = (spent / budget.total_amount * 100) if budget.total_amount > 0 else 0

        # Calculate days remaining
        today = date.today()
        days_remaining = (budget.end_date - today).days if budget.end_date > today else 0

        # Calculate projections
        days_elapsed = (today - budget.start_date).days or 1
        daily_average = spent / days_elapsed
        projected_spend = daily_average * (budget.end_date - budget.start_date).days

        # Get category breakdown
        category_breakdown = await self.service.get_category_breakdown(budget_id)

        return BudgetSummary(
            budget_id=budget_id,
            total_budget=budget.total_amount,
            total_spent=spent,
            total_remaining=remaining,
            percentage_used=percentage_used,
            days_remaining=days_remaining,
            daily_average_spent=daily_average,
            projected_total_spend=projected_spend,
            status=self._determine_status(percentage_used, days_remaining),
            category_breakdown=category_breakdown
        )

    async def update_allocations(
        self,
        user_id: str,
        budget_id: str,
        data: BudgetAllocationRequest
    ) -> BudgetResponse:
        """Update budget category allocations."""
        budget = await self.service.update_allocations(
            budget_id,
            user_id=user_id,
            allocations=data.allocations
        )
        return BudgetResponse.model_validate(budget)

    def _determine_status(
        self,
        percentage_used: float,
        days_remaining: int
    ) -> str:
        """Determine budget status based on usage and time."""
        if percentage_used >= 100:
            return "over_budget"
        elif percentage_used >= 90:
            return "critical"
        elif percentage_used >= 75 and days_remaining > 7:
            return "warning"
        return "on_track"
```

```python
# report_handler.py
from typing import Optional
from datetime import date
from decimal import Decimal
import io

from papita_txnsmodel import (
    TransactionService,
    BudgetService,
    AccountService
)
from api.schemas.report import (
    SpendingReport,
    BudgetPerformanceReport,
    CashFlowReport,
    TrendsReport,
    ReportExportFormat
)

class ReportHandler:
    """Handler for report generation logic."""

    def __init__(
        self,
        transaction_service: TransactionService,
        budget_service: BudgetService,
        account_service: AccountService
    ):
        self.transaction_service = transaction_service
        self.budget_service = budget_service
        self.account_service = account_service

    async def generate_spending_report(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        group_by: str = "category",
        account_id: Optional[str] = None
    ) -> SpendingReport:
        """Generate spending analysis report."""
        transactions = await self.transaction_service.get_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )

        # Calculate totals
        total_spending = sum(
            t.amount for t in transactions
            if t.transaction_type == "expense"
        )
        total_income = sum(
            t.amount for t in transactions
            if t.transaction_type == "income"
        )

        # Group by specified dimension
        breakdown = self._group_transactions(transactions, group_by)

        # Calculate daily trend
        trend = self._calculate_daily_trend(transactions, start_date, end_date)

        return SpendingReport(
            period={"start_date": start_date, "end_date": end_date},
            total_spending=total_spending,
            total_income=total_income,
            net_savings=total_income - total_spending,
            breakdown=breakdown,
            trend=trend
        )

    async def generate_budget_performance_report(
        self,
        user_id: str,
        budget_id: Optional[str] = None,
        period: Optional[str] = None
    ) -> BudgetPerformanceReport:
        """Generate budget performance analysis."""
        if budget_id:
            budgets = [await self.budget_service.get_by_id(budget_id, user_id)]
        else:
            budgets = await self.budget_service.get_by_period(user_id, period)

        budget_analyses = []
        for budget in budgets:
            spent = await self.budget_service.calculate_spent(budget.id)
            categories = await self.budget_service.get_category_breakdown(budget.id)

            budget_analyses.append({
                "budget_id": budget.id,
                "budget_name": budget.name,
                "total_budget": budget.total_amount,
                "total_spent": spent,
                "variance": budget.total_amount - spent,
                "performance_score": self._calculate_performance_score(budget, spent),
                "categories": categories
            })

        return BudgetPerformanceReport(budgets=budget_analyses)

    async def generate_cash_flow_report(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> CashFlowReport:
        """Generate cash flow analysis."""
        accounts = await self.account_service.get_all(user_id=user_id)

        opening_balance = await self.account_service.get_total_balance_at_date(
            user_id, start_date
        )
        closing_balance = await self.account_service.get_total_balance_at_date(
            user_id, end_date
        )

        transactions = await self.transaction_service.get_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        total_inflows = sum(
            t.amount for t in transactions
            if t.transaction_type == "income"
        )
        total_outflows = sum(
            t.amount for t in transactions
            if t.transaction_type == "expense"
        )

        # Calculate per-account breakdown
        by_account = []
        for account in accounts:
            account_txns = [t for t in transactions if t.account_id == account.id]
            inflows = sum(t.amount for t in account_txns if t.transaction_type == "income")
            outflows = sum(t.amount for t in account_txns if t.transaction_type == "expense")
            by_account.append({
                "account_id": account.id,
                "account_name": account.name,
                "inflows": inflows,
                "outflows": outflows,
                "net": inflows - outflows
            })

        return CashFlowReport(
            period={"start_date": start_date, "end_date": end_date},
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_inflows=total_inflows,
            total_outflows=total_outflows,
            net_cash_flow=total_inflows - total_outflows,
            by_account=by_account
        )

    async def export_report(
        self,
        user_id: str,
        report_type: str,
        format: ReportExportFormat,
        start_date: date,
        end_date: date
    ) -> io.BytesIO:
        """Export report in specified format."""
        # Generate the appropriate report
        if report_type == "spending":
            report_data = await self.generate_spending_report(
                user_id, start_date, end_date
            )
        elif report_type == "budget_performance":
            report_data = await self.generate_budget_performance_report(user_id)
        elif report_type == "cash_flow":
            report_data = await self.generate_cash_flow_report(
                user_id, start_date, end_date
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        # Export to specified format
        if format == ReportExportFormat.CSV:
            return self._export_to_csv(report_data)
        elif format == ReportExportFormat.XLSX:
            return self._export_to_xlsx(report_data)
        elif format == ReportExportFormat.PDF:
            return self._export_to_pdf(report_data)

        raise ValueError(f"Unknown export format: {format}")

    def _group_transactions(self, transactions, group_by: str) -> list:
        """Group transactions by specified dimension."""
        # Implementation for grouping logic
        pass

    def _calculate_daily_trend(self, transactions, start_date, end_date) -> list:
        """Calculate daily spending/income trend."""
        # Implementation for trend calculation
        pass

    def _calculate_performance_score(self, budget, spent) -> int:
        """Calculate budget performance score (0-100)."""
        if budget.total_amount == 0:
            return 100
        ratio = spent / budget.total_amount
        if ratio <= 0.8:
            return 100
        elif ratio <= 1.0:
            return int(100 - (ratio - 0.8) * 100)
        else:
            return max(0, int(100 - (ratio - 1.0) * 200))

    def _export_to_csv(self, report_data) -> io.BytesIO:
        """Export report data to CSV format."""
        # Implementation
        pass

    def _export_to_xlsx(self, report_data) -> io.BytesIO:
        """Export report data to Excel format."""
        # Implementation
        pass

    def _export_to_pdf(self, report_data) -> io.BytesIO:
        """Export report data to PDF format."""
        # Implementation
        pass
```

### 4. Router Layer (`api/routers/`)

Routers define HTTP endpoints and delegate business logic to handlers.

```python
# routers/v1/transactions.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import date

from api.dependencies.auth import get_current_active_user
from api.dependencies.pagination import get_pagination, PaginationParams
from api.dependencies.transaction_deps import get_transaction_service
from api.handlers.transaction_handler import TransactionHandler
from api.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilter,
    BulkTransactionCreate,
    BulkTransactionResponse,
    SplitTransactionRequest
)
from api.schemas.common import PaginatedResponse

from papita_txnsmodel import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def get_transaction_handler(
    service: TransactionService = Depends(get_transaction_service)
) -> TransactionHandler:
    return TransactionHandler(service)

@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    summary="Get all transactions",
    description="Retrieve paginated list of transactions with optional filters"
)
async def get_transactions(
    pagination: PaginationParams = Depends(get_pagination),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    budget_id: Optional[str] = Query(None, description="Filter by budget"),
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    search: Optional[str] = Query(None, description="Search in description"),
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    filters = TransactionFilter(
        account_id=account_id,
        category_id=category_id,
        budget_id=budget_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search
    )
    return await handler.get_transactions(
        user_id=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )

@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="Retrieve a specific transaction by its ID"
)
async def get_transaction(
    transaction_id: str,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    transaction = await handler.get_transaction_by_id(
        user_id=current_user,
        transaction_id=transaction_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction

@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transaction",
    description="Create a new transaction"
)
async def create_transaction(
    data: TransactionCreate,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    return await handler.create_transaction(
        user_id=current_user,
        data=data
    )

@router.post(
    "/bulk",
    response_model=BulkTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create transactions",
    description="Create multiple transactions at once"
)
async def bulk_create_transactions(
    data: BulkTransactionCreate,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    return await handler.bulk_create_transactions(
        user_id=current_user,
        data=data
    )

@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    description="Update an existing transaction"
)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    transaction = await handler.update_transaction(
        user_id=current_user,
        transaction_id=transaction_id,
        data=data
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction

@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transaction",
    description="Delete a transaction"
)
async def delete_transaction(
    transaction_id: str,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    deleted = await handler.delete_transaction(
        user_id=current_user,
        transaction_id=transaction_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

@router.post(
    "/{transaction_id}/split",
    response_model=list[TransactionResponse],
    summary="Split transaction",
    description="Split a transaction into multiple parts"
)
async def split_transaction(
    transaction_id: str,
    data: SplitTransactionRequest,
    current_user: str = Depends(get_current_active_user),
    handler: TransactionHandler = Depends(get_transaction_handler)
):
    return await handler.split_transaction(
        user_id=current_user,
        transaction_id=transaction_id,
        data=data
    )
```

## 🚀 Application Entry Point

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.config.settings import get_settings
from api.routers.router import api_router
from api.core.exceptions import setup_exception_handlers
from api.core.middleware import setup_middleware

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Save Ma Money API...")
    yield
    # Shutdown
    print("Shutting down Save Ma Money API...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Budgeting and Accounting System API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
setup_middleware(app)

# Exception Handlers
setup_exception_handlers(app)

# Include Routers
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

## 📦 Integration with papita_txnsmodel

The `papita_txnsmodel` library provides all core functionality:

```python
# Example imports from papita_txnsmodel
from papita_txnsmodel import (
    # Models
    Transaction,
    Budget,
    Account,
    Category,
    Movement,

    # Enums
    TransactionType,
    MovementStatus,
    BudgetPeriod,

    # Repositories
    TransactionRepository,
    BudgetRepository,
    AccountRepository,
    CategoryRepository,
    MovementRepository,

    # Services
    TransactionService,
    BudgetService,
    AccountService,
    CategoryService,
    MovementService,

    # Database utilities
    get_session_factory,
    init_database
)
```

## 📊 Technology Stack

| Component        | Technology                  |
| ---------------- | --------------------------- |
| Framework        | FastAPI 0.109+              |
| Data Validation  | Pydantic v2                 |
| Data Layer       | papita_txnsmodel            |
| Authentication   | JWT (python-jose)           |
| Testing          | Pytest + httpx              |
| Documentation    | OpenAPI 3.0 (Swagger/ReDoc) |
| Containerization | Docker                      |

## 🏃 Quick Start

```bash
# Clone repository
git clone https://github.com/Elmorralito/save-ma-money.git
cd save-ma-money

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install papita_txnsmodel (local)
pip install -e ./modules/model

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start the server
uvicorn api.main:app --reload
```

## 📚 API Documentation

Once the server is running, access the documentation at:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json
