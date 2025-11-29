"""Papita Transactions Model Library

This library provides a comprehensive data modeling and database interaction framework
for financial transaction systems. It implements a clean, layered architecture with
strong typing, validation, and database integration features.

Architecture Overview:
    The library follows a multi-layered architecture:

    1. Model Layer:
        - SQLModel-based database models with schema configuration
        - Common fields like active status and deletion tracking
        - Defined in model/ package

    2. Access Layer:
        - Data Transfer Objects (DTOs) for validation and serialization
        - Repository pattern for database operations
        - Type-specific repositories with CRUD operations
        - Defined in access/ package

    3. Service Layer:
        - Business logic combining repository operations
        - Transaction management and validation
        - Support for bulk operations and upserts
        - Defined in services/ package

    4. Handler Layer:
        - Application interface components
        - Error handling strategies
        - Service management and configuration
        - Defined in handlers/ package

Key Features:
    - Type-safe database interaction through SQLModel and Pydantic
    - Support for multiple database dialects (PostgreSQL, DuckDB)
    - Soft deletion and record tracking
    - Advanced upsert operations with conflict resolution
    - Flexible error handling strategies
    - Comprehensive validation through Pydantic models
    - Batch processing for performance optimization
    - Transaction integrity through session management

Database Integration:
    - Connection management with SQLDatabaseConnector
    - Session management and transaction control
    - Dialect-specific upsert operations
    - Support for both hard and soft deletions

Utility Components:
    - DataFrame standardization with Pydantic models
    - Class inspection and selection utilities
    - Configurable error handling strategies
    - DTO serialization helpers

The library serves as the foundation for financial data management applications,
providing a robust, type-safe approach to handling transactions and related entities.
"""

from .__meta__ import __authors__, __configs__, __version__  # noqa: F401

LIB_NAME = __name__
