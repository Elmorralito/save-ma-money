"""Schemas for self-hosted single-owner AI agent routes (``/api/v1/ai/*``)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIConnectionStatus(BaseModel):
    """Readiness and type metadata for one enabled AI connection (API or CLI)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["api", "cli"]
    provider: str
    model: str | None = None
    ready: bool


class AIStatusResponse(BaseModel):
    """Availability and enabled API/CLI connections for the self-hosted AI sidecar."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    available: bool
    provider: str | None = None
    model: str | None = None
    default_connection: str | None = None
    connections: list[AIConnectionStatus] = Field(default_factory=list)
    single_owner_enforced: bool


class AIChatRequest(BaseModel):
    """User prompt submitted to the self-hosted AI sidecar."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=4000)
    connection: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9:_-]+$")
    include_financial_context: bool = True
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class AIChatResponse(BaseModel):
    """Non-streaming reply from the self-hosted AI sidecar."""

    model_config = ConfigDict(extra="forbid")

    reply: str
    connection: str | None = None
    kind: Literal["api", "cli"] | None = None
    provider: str
    model: str | None = None
    context_included: bool


__all__ = [
    "AIChatRequest",
    "AIChatResponse",
    "AIConnectionStatus",
    "AIStatusResponse",
]
