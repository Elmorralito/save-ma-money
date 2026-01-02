# Papita Transactions Data Model

Welcome to the **backbone of financial data integrity** for the `save-ma-finances` ecosystem. The `papita-txnsmodel` library is a production-grade framework engineered to solve the inherent challenges of financial data fragmentation. It bridges the gap between disparate, messy financial exports and a clean, structured, and auditable data warehouse.

![](../../docs/postgres_papita_transactions.png)

## Overview

In the world of personal and professional finance, data often arrives in heterogeneous formats: banking CSVs, API JSONs, and manual spreadsheets. `papita-txnsmodel` acts as the **central nervous system** for this data, providing a unified language that translates these "raw signals" into actionable logical entities.

### The Problem Space

Traditional financial tracking often suffers from:

- **Data Fragmentation**: Different banks used different naming conventions.
- **Lack of Schema Enforcement**: Silent failures when importing non-standard data.
- **High Friction in Switching Backends**: Developers being locked into a specific database (e.g., PostgreSQL vs. SQLite).

### Our Solution

`papita-txnsmodel` addresses these by providing a **Resilient, Layered Data Pipeline**:

1.  **Strict Type Safety**: Every field is validated at the point of entry.
2.  **Dialect Agnosticism**: Performance on PostgreSQL for the heavy lifting, convenience of DuckDB for the local experimentation.
3.  **Conflict-Aware Ingestion**: Sophisticated upsert logic that understands when to update a record and when to respect existing data.

### Core Philosophy

- **Explicit over Implicit**: Schemas are centralized, and relationships are clearly defined to prevent "ghost records" or orphan transactions.
- **Built-in Traceability**: Support for soft deletions (`deleted_at`) and active flags means you never lose data, even when "deleting" it.
- **Developer Efficiency**: Standardized CRUD operations and Pandas integration allow developers to focus on financial logic rather than SQL boilerplate.

## Architectural Layers

The library follows a strict four-layer architecture to ensure maintainability and scalability.

### 1. Model Layer (`papita_txnsmodel.model`)

This layer defines the "Source of Truth" using [SQLModel](https://sqlmodel.tiangolo.com/).

- **BaseSQLModel**: Every entity inherits from this base class, which automatically injects:
  - `active` (bool): A flag for logical status.
  - `deleted_at` (timestamp): Tracking the exact moment of soft deletion.
  - `SCHEMA_NAME`: Centralized schema management (defaults to `papita_transactions`).
- **Design Pattern**: Distinguishes between **Templates** (e.g., `IdentifiedTransactions` for recurring setups) and **Instances** (e.g., `Transactions` for actual money movements).
- **Relationships**: Rich SQLAlchemy-backed relationships with cascade delete configurations and many-to-one linkings.

### 2. Access Layer (`papita_txnsmodel.access`)

The bridge between the database and the application logic, focusing on data shapes and raw queries.

- **DTO (Data Transfer Objects)**:
  - `TableDTO`: Standardizes validation using Pydantic. Includes methods like `from_dao()` and `to_dao()` for seamless conversion.
  - `CoreTableDTO`: Adds common fields like `name`, `description`, and `tags` (with automated normalization).
- **Repository Pattern**:
  - `BaseRepository`: Implements sophisticated CRUD logic, including `soft_delete_records`, `hard_delete_records`, and complex `run_query` implementations.
  - **Pandas Integration**: Native support for returning query results as standardized DataFrames via `get_records`.

### 3. Service Layer (`papita_txnsmodel.services`)

Orchestrates business logic and maintains transaction integrity across multiple repositories.

- **BaseService**: Acts as the primary entry point for application developers.
  - **Validation**: Methods like `check_expected_dto_type` ensure that only valid data reaches the lower layers.
  - **Advanced Bulk Upserts**: Features a tolerance mechanism (`missing_upsertions_tol`) that allows developers to set an acceptable threshold for partial failures during high-volume data ingestion.
  - Support for `get_or_create` logic to simplify entity management.

### 4. Handler Layer (`papita_txnsmodel.handlers`)

Provides the interface for high-level data pipelines (e.g., CSV loaders, external API integrations).

- **AbstractHandler**: A generic base (parameterized by Service type) that defines strict `load()` and `dump()` contracts.
- **Dynamic Discovery**:
  - `HandlerFactory`: Automatically scans for concrete handler implementations.
  - `HandlerRegistry`: A singleton that manages handlers using a labeling system. Handlers can be retrieved by multiple labels (e.g., "csv", "transactions", "bank-a").
- **Extensibility**: Developers can add new loaders just by inheriting from `AbstractHandler` and decorating with appropriate labels.

## Database Integration & Conflict Resolution

The database layer is designed for extreme flexibility, particularly for the **Upsert** operation (Insert or Update if exists).

### SQLDatabaseConnector

A robust connection manager that handles:

- **Singleton Engine**: Efficiently manages SQLAlchemy engine instances.
- **Auto-session Decoration**: Uses `@SQLDatabaseConnector.connect` to handle session lifecycle automatically.
- **DuckDB & PostgreSQL**: Seamless switching between a lightweight local DuckDB backend and a production PostgreSQL cluster.

### Upsert Engine

Based on a factory pattern that matches the database dialect:

- **PostgreSQLUpserter**: Leverages `ON CONFLICT DO UPDATE` or `DO NOTHING` syntax.
- **DuckDBUpserter**: Inherits from PostgreSQL logic but adapts to DuckDB specificities.
- **OnConflict Strategies**: Developers can choose `UPDATE`, `NOTHING`, or `RAISE` via the `OnUpsertConflictDo` enum.

## Utilities & Helpers (`papita_txnsmodel.utils`)

- **ClassDiscovery**: Powerful introspection to find subclasses across modules (used in factories).
- **DataUtils**: Functions like `standardize_dataframe` ensure Pandas data aligns perfectly with Pydantic model definitions.
- **ModelUtils**: Built-in validators for shared fields like `tags` and `boolean` strings.

## Usage Example

### 1. Connecting to the Database

```python
from papita_txnsmodel.database.connector import SQLDatabaseConnector

# Connect to a local DuckDB file for development
SQLDatabaseConnector.establish(connection="./data/my_finance.duckdb")
```

### 2. High-Level Data Ingestion

```python
import pandas as pd
from papita_txnsmodel.services.transactions import TransactionService

# Load data from a raw source (e.g., CSV)
raw_data = pd.read_csv("bank_export.csv")

# Initialize the service
txn_service = TransactionService()

# Upsert 10,000 records with a 1% failure tolerance
# If more than 100 records fail, a RuntimeError is raised.
txn_service.upsert_records(
    df=raw_data,
    on_conflict_do="UPDATE",
    missing_upsertions_tol=0.01
)
```

### 3. Implementing a Custom Handler

```python
from papita_txnsmodel.handlers.abstract import AbstractHandler
from papita_txnsmodel.services.transactions import TransactionService

class MyCustomBankHandler(AbstractHandler[TransactionService]):
    @classmethod
    def labels(cls):
        return ("my-bank", "transactions")

    def load(self, data, **kwargs):
        # Implementation of parsing logic...
        return self

    def dump(self, **kwargs):
        # Implementation of persisting logic...
        return self
```
