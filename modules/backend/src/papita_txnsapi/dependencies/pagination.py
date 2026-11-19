"""Pagination query dependencies.

Provides a shared Pydantic model and FastAPI dependency for ``skip``/``limit`` query
parameters on list endpoints. Enforces non-negative skip and bounded page size.

Key exports:
    PaginationParams: Validated skip/limit pair for repository queries.
    get_pagination: FastAPI dependency that parses query parameters into ``PaginationParams``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Validated skip/limit pair for offset-based list pagination.

    Attributes:
        skip: Number of records to skip from the start of the result set (>= 0).
        limit: Maximum records to return per page (1--500 inclusive).
    """

    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


def get_pagination(
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximum records to return")] = 100,
) -> PaginationParams:
    """Resolve ``skip`` and ``limit`` query parameters into a ``PaginationParams`` model.

    Args:
        skip: Query parameter — records to skip (default 0).
        limit: Query parameter — max records to return (default 100, max 500).

    Returns:
        Validated ``PaginationParams`` instance for downstream service calls.
    """
    return PaginationParams(skip=skip, limit=limit)
