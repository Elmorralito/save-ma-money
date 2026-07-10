"""Shared API response and error schemas.

Reusable envelopes for list pagination, structured errors, and deferred MVP
endpoints. Domain routers compose ``PaginatedResponse[T]`` with resource-specific
item types.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload for non-validation failures.

    Attributes:
        detail: Human-readable summary of the failure.
        errors: Optional list of field-level or auxiliary error objects.
    """

    detail: str
    errors: list[dict[str, object]] | None = None


class DeferredResponse(BaseModel):
    """501 response body for deferred MVP endpoints.

    Attributes:
        detail: Default message pointing to the API mapping doc.
        deferred_reason: Optional override explaining why the route is not implemented.
    """

    detail: str = "Not implemented in MVP — see PPT-031-api-model-mapping.md"
    deferred_reason: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard list envelope for tenant-scoped collections.

    Attributes:
        items: Page of resources for the current ``skip``/``limit`` window.
        total: Total matching rows before pagination (not just page size).
        skip: Number of leading rows omitted from the result set.
        limit: Maximum rows requested per page (must be at least 1).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T] = Field(default_factory=list)
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
