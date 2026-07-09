"""Pagination query dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Shared skip/limit pagination for list endpoints."""

    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


def get_pagination(
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximum records to return")] = 100,
) -> PaginationParams:
    """Resolve pagination query parameters for routers."""
    return PaginationParams(skip=skip, limit=limit)
