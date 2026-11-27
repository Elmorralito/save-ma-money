"""Schemas for self-hosted single-owner AI agent routes (``/api/v1/ai/*``)."""

from __future__ import annotations

from typing import Any, Literal

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
    module: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9:_-]+$")
    view: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9:_-]+$")
    control: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9:_-]+$")
    locale: str | None = Field(default=None, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    surface_context: dict[str, Any] | None = None


class AIChatResponse(BaseModel):
    """Non-streaming reply from the self-hosted AI sidecar."""

    model_config = ConfigDict(extra="forbid")

    reply: str
    connection: str | None = None
    kind: Literal["api", "cli"] | None = None
    provider: str
    model: str | None = None
    context_included: bool


AIMode = Literal["sidecar", "lan_local", "api_key"]


class AIConfigResponse(BaseModel):
    """Owner-scoped AI/LLM configuration (secrets are never returned in plaintext)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: AIMode = "sidecar"
    default_connection: str = "cli:agy"
    model: str | None = None
    base_url: str | None = None
    include_financial_context_by_default: bool = True
    reports_ai_enabled: bool = True
    payment_dues_ai_enabled: bool = True
    cli_permission_granted: bool = False
    lan_permission_granted: bool = False
    api_permission_granted: bool = False
    has_api_key: bool = False
    api_key_hint: str | None = None


class AIConfigUpdateRequest(BaseModel):
    """Update owner-scoped AI/LLM provider, CLI/LAN/API mode, model, or encrypted API key."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    mode: AIMode | None = None
    default_connection: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9:_-]+$")
    model: str | None = Field(default=None, max_length=128)
    base_url: str | None = Field(default=None, max_length=256)
    include_financial_context_by_default: bool | None = None
    reports_ai_enabled: bool | None = None
    payment_dues_ai_enabled: bool | None = None
    cli_permission_granted: bool | None = None
    lan_permission_granted: bool | None = None
    api_permission_granted: bool | None = None
    api_key: str | None = Field(default=None, max_length=512)
    clear_api_key: bool = False


class AIModelOption(BaseModel):
    """Selectable exact model ID and readable label."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class AIModelsRequest(BaseModel):
    """Discover exact model IDs for a CLI/sidecar, LAN/local model, or direct API provider."""

    model_config = ConfigDict(extra="forbid")

    mode: AIMode = "sidecar"
    connection: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9:_-]+$")
    base_url: str | None = Field(default=None, max_length=256)
    api_key: str | None = Field(default=None, max_length=512)


class AIModelsResponse(BaseModel):
    """Available exact model IDs discovered for the requested provider connection."""

    model_config = ConfigDict(extra="forbid")

    connection: str
    mode: AIMode
    ready: bool
    source: Literal["live", "curated"] = "live"
    models: list[AIModelOption] = Field(default_factory=list)
    default_model: str | None = None


__all__ = [
    "AIChatRequest",
    "AIChatResponse",
    "AIConfigResponse",
    "AIConfigUpdateRequest",
    "AIConnectionStatus",
    "AIModelOption",
    "AIModelsRequest",
    "AIModelsResponse",
    "AIStatusResponse",
]
