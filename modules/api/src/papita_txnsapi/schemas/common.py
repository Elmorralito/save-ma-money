"""Shared API response and error schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload for non-validation failures."""

    detail: str
    errors: list[dict[str, object]] | None = None


class DeferredResponse(BaseModel):
    """501 response body for deferred MVP endpoints."""

    detail: str = "Not implemented in MVP — see PPT-031-api-model-mapping.md"
    deferred_reason: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard list envelope for tenant-scoped collections."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T] = Field(default_factory=list)
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
