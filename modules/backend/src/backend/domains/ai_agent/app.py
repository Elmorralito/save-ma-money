"""Internal FastAPI sidecar service for self-hosted AI agent execution.

Runs on the private Compose network (``papita-local-net``) under the optional
``ai-agent`` profile. Authenticates callers from ``papita_txnsapi`` via a shared
secret header (``X-Papita-AI-Secret``) and never connects to PostgreSQL directly.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.domains.ai_agent.adapters import (
    AIAgentAdapter,
    AIAgentError,
    AIAgentRegistry,
    ConnectionKind,
    build_registry_from_env,
)

_SHARED_SECRET_HEADER = "X-Papita-AI-Secret"


class SidecarPromptRequest(BaseModel):
    """Internal prompt payload forwarded by ``papita_txnsapi``."""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str = Field(default="", max_length=16_000)
    user_prompt: str = Field(min_length=1, max_length=8_000)
    connection: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)


class SidecarModelItem(BaseModel):
    """Discoverable model option exposed by a sidecar adapter."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class SidecarModelsResponse(BaseModel):
    """Models returned by ``GET /models`` for a specific sidecar connection."""

    model_config = ConfigDict(extra="forbid")

    connection: str
    kind: ConnectionKind
    provider: str
    ready: bool
    models: list[SidecarModelItem] = Field(default_factory=list)


class SidecarPromptResponse(BaseModel):
    """Non-streaming sidecar response."""

    model_config = ConfigDict(extra="forbid")

    reply: str
    connection: str
    kind: ConnectionKind
    provider: str
    model: str | None = None


class SidecarConnectionHealth(BaseModel):
    """Readiness state for one enabled API or CLI connection."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: ConnectionKind
    provider: str
    model: str | None = None
    ready: bool


class SidecarHealthResponse(BaseModel):
    """Sidecar readiness payload across all enabled API + CLI connections."""

    model_config = ConfigDict(extra="forbid")

    status: str
    provider: str
    model: str | None = None
    ready: bool
    default_connection: str
    connections: list[SidecarConnectionHealth] = Field(default_factory=list)


def _verify_shared_secret(
    x_papita_ai_secret: Annotated[str | None, Header(alias=_SHARED_SECRET_HEADER)] = None,
) -> None:
    """Enforce internal shared-secret auth when ``AI_AGENT_SHARED_SECRET`` is set."""
    expected = (os.environ.get("AI_AGENT_SHARED_SECRET") or "").strip()
    if not expected:
        return
    provided = (x_papita_ai_secret or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid AI sidecar secret")


def create_sidecar_app(
    registry: AIAgentRegistry | None = None,
    *,
    adapter: AIAgentAdapter | None = None,
) -> FastAPI:
    """Build the internal AI sidecar FastAPI application."""
    sidecar = FastAPI(title="Papita Self-Hosted AI Sidecar", docs_url=None, redoc_url=None)
    if registry is not None:
        resolved_registry = registry
    elif adapter is not None:
        resolved_registry = AIAgentRegistry({adapter.provider_name: adapter}, default_id=adapter.provider_name)
    else:
        resolved_registry = build_registry_from_env()

    def _resolve(connection_id: str | None) -> tuple[str, AIAgentAdapter]:
        try:
            selected = resolved_registry.get(connection_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        resolved_id = (
            connection_id.strip().lower() if connection_id and connection_id.strip() else resolved_registry.default_id
        )
        return resolved_id, selected

    @sidecar.get("/health", response_model=SidecarHealthResponse)
    async def health() -> SidecarHealthResponse:
        ids = resolved_registry.ids()
        adapters = [resolved_registry.get(cid) for cid in ids]
        checks = await asyncio.gather(*(item.health() for item in adapters))
        connections = [
            SidecarConnectionHealth(
                id=cid,
                kind=item.connection_kind,
                provider=item.provider_name,
                model=item.model_name,
                ready=bool(is_ready),
            )
            for cid, item, is_ready in zip(ids, adapters, checks, strict=True)
        ]
        default_item = next(c for c in connections if c.id == resolved_registry.default_id)
        any_ready = any(c.ready for c in connections)
        return SidecarHealthResponse(
            status="ok" if any_ready else "degraded",
            provider=default_item.provider,
            model=default_item.model,
            ready=default_item.ready,
            default_connection=resolved_registry.default_id,
            connections=connections,
        )

    @sidecar.get(
        "/models",
        response_model=SidecarModelsResponse,
        dependencies=[Depends(_verify_shared_secret)],
    )
    async def list_models(connection: str | None = None) -> SidecarModelsResponse:
        conn_id, selected = _resolve(connection)
        is_ready = bool(await selected.health())
        discovered = await selected.list_models() if is_ready else []
        return SidecarModelsResponse(
            connection=conn_id,
            kind=selected.connection_kind,
            provider=selected.provider_name,
            ready=is_ready,
            models=[SidecarModelItem(id=item.id, label=item.label) for item in discovered],
        )

    @sidecar.post(
        "/respond",
        response_model=SidecarPromptResponse,
        dependencies=[Depends(_verify_shared_secret)],
    )
    async def respond(payload: SidecarPromptRequest) -> SidecarPromptResponse:
        conn_id, selected = _resolve(payload.connection)
        try:
            result = await selected.generate(
                system_prompt=payload.system_prompt,
                user_prompt=payload.user_prompt,
                model=payload.model,
            )
        except AIAgentError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return SidecarPromptResponse(
            reply=result.reply,
            connection=conn_id,
            kind=selected.connection_kind,
            provider=result.provider,
            model=result.model,
        )

    @sidecar.post(
        "/stream",
        dependencies=[Depends(_verify_shared_secret)],
    )
    async def stream(payload: SidecarPromptRequest) -> StreamingResponse:
        _conn_id, selected = _resolve(payload.connection)

        async def _events() -> AsyncIterator[str]:
            try:
                async for chunk in selected.stream(
                    system_prompt=payload.system_prompt,
                    user_prompt=payload.user_prompt,
                    model=payload.model,
                ):
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            except AIAgentError as exc:
                yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"

        return StreamingResponse(_events(), media_type="text/event-stream")

    return sidecar


app = create_sidecar_app()
