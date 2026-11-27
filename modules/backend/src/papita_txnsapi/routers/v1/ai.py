"""Self-hosted single-owner AI agent gateway routes (``/api/v1/ai/*``).

Thin FastAPI adapter over ``backend.domains.ai_agent.{guardrails,transport}``.
Enforces:
- Opt-in enablement (``AI_AGENT_ENABLED=true``) and fail-closed single-owner lock
  (``AI_AGENT_ALLOWED_OWNER_ID``).
- Per-transport user integration permissions (CLI, LAN/local models, direct cloud API).
- Read-only redacted context framing and SSRF URL validation.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.domains.ai_agent.guardrails import (
    AIGuardrailError,
    SurfaceContextSpec,
    build_guarded_system_prompt,
    check_module_enablement,
    check_transport_permission,
    validate_endpoint_url,
)
from backend.domains.ai_agent.transport import (
    DEFAULT_PROVIDER_MODELS,
    DIRECT_HTTP_PROVIDERS,
    LAN_LOCAL_PROVIDERS,
    AITransportError,
    AITransportGateway,
    classify_transport,
)
from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.services import get_report_service, get_users_service
from papita_txnsapi.routers.v1.ingestion import _fernet_for_settings
from papita_txnsapi.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIConfigResponse,
    AIConfigUpdateRequest,
    AIConnectionStatus,
    AIMode,
    AIModelOption,
    AIModelsRequest,
    AIModelsResponse,
    AIStatusResponse,
)
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.reports import ReportService
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["AI Agent"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


def _require_ai_owner(owner: UsersDTO, settings: Settings) -> None:
    """Enforce opt-in enablement and strict single-owner isolation (fail-closed)."""
    if not settings.AI_AGENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Self-hosted AI agent is disabled",
        )
    allowed_owner = (settings.AI_AGENT_ALLOWED_OWNER_ID or "").strip()
    if not allowed_owner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_AGENT_ALLOWED_OWNER_ID must be configured for single-owner isolation",
        )
    if str(owner.id) != allowed_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-hosted AI agent is restricted to the configured single owner",
        )


def _gateway_for_settings(settings: Settings) -> AITransportGateway:
    return AITransportGateway(
        sidecar_url=settings.AI_AGENT_URL,
        sidecar_secret=settings.AI_AGENT_SHARED_SECRET,
        qwen_finance_base_url=settings.QWEN_FINANCE_BASE_URL,
        qwen_finance_model=settings.QWEN_FINANCE_MODEL,
        timeout_seconds=settings.AI_AGENT_TIMEOUT_SECONDS,
    )


def _read_ai_config(owner: UsersDTO) -> dict[str, Any]:
    raw = (owner.preferences or {}).get("ai_config")
    return dict(raw) if isinstance(raw, dict) else {}


def _resolve_mode(raw: Any) -> AIMode:
    if raw == "api_key":
        return "api_key"
    if raw == "lan_local":
        return "lan_local"
    return "sidecar"


def _config_response_from_dict(cfg: dict[str, Any]) -> AIConfigResponse:
    return AIConfigResponse(
        enabled=bool(cfg.get("enabled", True)),
        mode=_resolve_mode(cfg.get("mode")),
        default_connection=str(cfg.get("default_connection") or "cli:agy"),
        model=cfg.get("model"),
        base_url=cfg.get("base_url"),
        include_financial_context_by_default=bool(cfg.get("include_financial_context_by_default", True)),
        reports_ai_enabled=bool(cfg.get("reports_ai_enabled", True)),
        payment_dues_ai_enabled=bool(cfg.get("payment_dues_ai_enabled", True)),
        cli_permission_granted=bool(cfg.get("cli_permission_granted", False)),
        lan_permission_granted=bool(cfg.get("lan_permission_granted", False)),
        api_permission_granted=bool(cfg.get("api_permission_granted", False)),
        has_api_key=bool(cfg.get("api_key_enc")),
        api_key_hint=cfg.get("api_key_hint"),
    )


def _mask_api_key(key: str) -> str:
    cleaned = key.strip()
    if len(cleaned) <= 8:
        return "••••"
    return f"{cleaned[:4]}••••{cleaned[-4:]}"


def _decrypt_owner_api_key(owner: UsersDTO, settings: Settings) -> str | None:
    cfg = _read_ai_config(owner)
    enc = cfg.get("api_key_enc")
    if not isinstance(enc, str) or not enc.strip():
        return None
    try:
        return _fernet_for_settings(settings).decrypt(enc.encode("ascii")).decode("utf-8")
    except Exception:  # pylint: disable=broad-except
        return None


def _assemble_system_prompt(
    *,
    owner: UsersDTO,
    report_service: ReportService,
    payload: AIChatRequest,
) -> tuple[str, bool]:
    snapshot: dict[str, Any] | None = None
    if payload.include_financial_context:
        try:
            health = report_service.financial_health(owner=owner, currency=payload.currency)
            snapshot = {
                "currency": health.currency,
                "reconciled_net_worth": health.reconciled_net_worth,
                "total_assets": health.total_assets,
                "total_liabilities": health.total_liabilities,
                "liquid_cash": health.liquid_cash,
                "monthly_operating_expenses": health.monthly_operating_expenses,
                "liquid_cash_runway_months": health.liquid_cash_runway_months,
                "monthly_debt_service": health.monthly_debt_service,
                "debt_to_asset_ratio": health.debt_to_asset_ratio,
            }
        except Exception:  # pylint: disable=broad-except
            logger.warning("Failed to build financial context snapshot for AI prompt owner_id=%s", owner.id)

    surface = SurfaceContextSpec(
        module=payload.module,
        view=payload.view,
        control=payload.control,
        locale=payload.locale,
        data=payload.surface_context,
    )
    return build_guarded_system_prompt(financial_snapshot=snapshot, surface_spec=surface)


@router.get("/config", response_model=AIConfigResponse)
def get_ai_config(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> AIConfigResponse:
    """Return owner's saved LLM/CLI/LAN configuration (API keys are never returned in plaintext)."""
    return _config_response_from_dict(_read_ai_config(owner))


@router.put("/config", response_model=AIConfigResponse)
def update_ai_config(
    payload: AIConfigUpdateRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> AIConfigResponse:
    """Persist owner's AI provider, mode, permissions, exact model ID, and Fernet-encrypted key."""
    cfg = _read_ai_config(owner)
    if payload.enabled is not None:
        cfg["enabled"] = payload.enabled
    if payload.mode is not None:
        cfg["mode"] = payload.mode
    if payload.default_connection is not None:
        cfg["default_connection"] = payload.default_connection.strip().lower()
    if payload.model is not None:
        cfg["model"] = payload.model.strip() or None
    if payload.base_url is not None:
        cleaned_url = payload.base_url.strip() or None
        if cleaned_url:
            # Validate against SSRF using the mode/connection that will consume the URL.
            effective_mode = _resolve_mode(payload.mode if payload.mode is not None else cfg.get("mode"))
            effective_conn = (
                str(
                    payload.default_connection
                    if payload.default_connection is not None
                    else cfg.get("default_connection") or ""
                )
                .strip()
                .lower()
            )
            allow_private = effective_mode == "lan_local" or effective_conn in LAN_LOCAL_PROVIDERS | {"openai_compat"}
            try:
                cleaned_url = validate_endpoint_url(cleaned_url, allow_private_lan=allow_private)
            except AIGuardrailError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        cfg["base_url"] = cleaned_url
    if payload.include_financial_context_by_default is not None:
        cfg["include_financial_context_by_default"] = payload.include_financial_context_by_default
    if payload.reports_ai_enabled is not None:
        cfg["reports_ai_enabled"] = payload.reports_ai_enabled
    if payload.payment_dues_ai_enabled is not None:
        cfg["payment_dues_ai_enabled"] = payload.payment_dues_ai_enabled
    if payload.cli_permission_granted is not None:
        cfg["cli_permission_granted"] = payload.cli_permission_granted
    if payload.lan_permission_granted is not None:
        cfg["lan_permission_granted"] = payload.lan_permission_granted
    if payload.api_permission_granted is not None:
        cfg["api_permission_granted"] = payload.api_permission_granted

    if payload.clear_api_key:
        cfg.pop("api_key_enc", None)
        cfg.pop("api_key_hint", None)
    elif payload.api_key is not None and payload.api_key.strip():
        raw_key = payload.api_key.strip()
        cfg["api_key_enc"] = _fernet_for_settings(settings).encrypt(raw_key.encode("utf-8")).decode("ascii")
        cfg["api_key_hint"] = _mask_api_key(raw_key)

    users_service.update_user_settings(owner=owner, preferences={"ai_config": cfg})
    return _config_response_from_dict(cfg)


@router.post("/models", response_model=AIModelsResponse)
async def list_ai_models(
    payload: AIModelsRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIModelsResponse:
    """Connect to the chosen CLI, LAN/local model (incl. Qwen Financial LoRA), or cloud API and return model IDs."""
    _require_ai_owner(owner, settings)
    owner_cfg = _read_ai_config(owner)
    transport_kind = classify_transport(payload.mode, payload.connection)
    denied = check_transport_permission(owner_cfg, transport_kind)
    if denied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied)

    api_key = (payload.api_key or "").strip() or (_decrypt_owner_api_key(owner, settings) or None)
    base_url = (payload.base_url or "").strip() or owner_cfg.get("base_url")
    gateway = _gateway_for_settings(settings)

    try:
        discovered = await gateway.list_models(
            mode=payload.mode,
            connection=payload.connection,
            base_url=base_url,
            api_key=api_key,
        )
    except AITransportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return AIModelsResponse(
        connection=discovered.connection,
        mode=payload.mode,
        ready=discovered.ready,
        source=discovered.source,
        models=[AIModelOption(id=m.id, label=m.label) for m in discovered.models],
        default_model=discovered.default_model,
    )


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIStatusResponse:
    """Return enabled and reachable AI connections across sidecar CLIs, LAN models, and direct APIs."""
    allowed_owner = (settings.AI_AGENT_ALLOWED_OWNER_ID or "").strip()
    single_owner_enforced = bool(allowed_owner)
    if not settings.AI_AGENT_ENABLED or not allowed_owner or str(owner.id) != allowed_owner:
        return AIStatusResponse(
            enabled=False,
            available=False,
            provider=None,
            model=None,
            single_owner_enforced=single_owner_enforced,
        )

    base_url = settings.AI_AGENT_URL.rstrip("/")
    connections: list[AIConnectionStatus] = []
    sidecar_provider: str | None = None
    sidecar_model: str | None = None
    sidecar_default: str | None = None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/health")
            if resp.status_code == 200:
                data = resp.json()
                raw_conns = data.get("connections") or []
                connections = [AIConnectionStatus.model_validate(item) for item in raw_conns]
                sidecar_provider = data.get("provider")
                sidecar_model = data.get("model")
                sidecar_default = data.get("default_connection")
    except httpx.HTTPError:
        logger.debug("AI sidecar health probe failed at %s", base_url)

    owner_cfg = _read_ai_config(owner)
    owner_mode = _resolve_mode(owner_cfg.get("mode"))
    owner_conn_id = str(owner_cfg.get("default_connection") or "").strip().lower()

    # Surface built-in LAN Qwen Financial LoRA or configured LAN/local connection
    if (
        owner_mode == "lan_local" and owner_conn_id in LAN_LOCAL_PROVIDERS and owner_cfg.get("lan_permission_granted")
    ) or (settings.QWEN_FINANCE_BASE_URL and not any(c.id == "qwen_finance" for c in connections)):
        lan_id = owner_conn_id if owner_mode == "lan_local" and owner_conn_id in LAN_LOCAL_PROVIDERS else "qwen_finance"
        lan_model = owner_cfg.get("model") or (
            settings.QWEN_FINANCE_MODEL if lan_id == "qwen_finance" else DEFAULT_PROVIDER_MODELS.get(lan_id)
        )
        if not any(c.id == lan_id for c in connections):
            connections.insert(
                0,
                AIConnectionStatus(
                    id=lan_id,
                    kind="api",
                    provider=lan_id,
                    model=lan_model,
                    ready=bool(owner_cfg.get("base_url") or settings.QWEN_FINANCE_BASE_URL),
                ),
            )
        if owner_mode == "lan_local":
            sidecar_default = lan_id
            sidecar_provider = sidecar_provider or lan_id
            sidecar_model = sidecar_model or lan_model

    # Surface user-configured direct cloud API provider
    if owner_mode == "api_key" and owner_conn_id in DIRECT_HTTP_PROVIDERS and owner_cfg.get("api_key_enc"):
        direct_model = owner_cfg.get("model") or DEFAULT_PROVIDER_MODELS.get(owner_conn_id)
        if not any(c.id == owner_conn_id for c in connections):
            connections.insert(
                0,
                AIConnectionStatus(
                    id=owner_conn_id,
                    kind="api",
                    provider=owner_conn_id,
                    model=direct_model,
                    ready=True,
                ),
            )
        sidecar_default = owner_conn_id
        sidecar_provider = sidecar_provider or owner_conn_id
        sidecar_model = sidecar_model or direct_model

    any_ready = any(c.ready for c in connections)
    return AIStatusResponse(
        enabled=True,
        available=any_ready,
        provider=sidecar_provider,
        model=sidecar_model,
        default_connection=sidecar_default,
        connections=connections,
        single_owner_enforced=True,
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    payload: AIChatRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> AIChatResponse:
    """Forward a guarded prompt (+ optional redacted snapshot & surface context) via AITransportGateway."""
    _require_ai_owner(owner, settings)
    if len(payload.prompt) > settings.AI_AGENT_MAX_PROMPT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Prompt exceeds maximum length of {settings.AI_AGENT_MAX_PROMPT_CHARS} characters",
        )

    owner_cfg = _read_ai_config(owner)
    owner_mode = _resolve_mode(owner_cfg.get("mode"))
    target_conn = (payload.connection or owner_cfg.get("default_connection") or "").strip().lower()
    transport_kind = classify_transport(owner_mode, target_conn)
    denied = check_transport_permission(owner_cfg, transport_kind)
    if denied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied)
    module_denied = check_module_enablement(owner_cfg, payload.module)
    if module_denied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=module_denied)

    system_prompt, context_included = _assemble_system_prompt(
        owner=owner,
        report_service=report_service,
        payload=payload,
    )
    gateway = _gateway_for_settings(settings)
    try:
        result = await gateway.chat(
            mode=owner_mode,
            connection=payload.connection or owner_cfg.get("default_connection"),
            model=owner_cfg.get("model"),
            base_url=owner_cfg.get("base_url"),
            api_key=_decrypt_owner_api_key(owner, settings),
            system_prompt=system_prompt,
            user_prompt=payload.prompt,
        )
    except AITransportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return AIChatResponse(
        reply=result.reply,
        connection=result.connection,
        kind=result.kind,
        provider=result.provider,
        model=result.model,
        context_included=context_included,
    )


@router.post("/chat/stream")
async def ai_chat_stream(
    payload: AIChatRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> StreamingResponse:
    """Stream SSE response chunks transparently through the AI transport gateway."""
    _require_ai_owner(owner, settings)
    if len(payload.prompt) > settings.AI_AGENT_MAX_PROMPT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Prompt exceeds maximum length of {settings.AI_AGENT_MAX_PROMPT_CHARS} characters",
        )

    owner_cfg = _read_ai_config(owner)
    owner_mode = _resolve_mode(owner_cfg.get("mode"))
    target_conn = (payload.connection or owner_cfg.get("default_connection") or "").strip().lower()
    transport_kind = classify_transport(owner_mode, target_conn)
    denied = check_transport_permission(owner_cfg, transport_kind)
    if denied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied)
    module_denied = check_module_enablement(owner_cfg, payload.module)
    if module_denied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=module_denied)

    system_prompt, _context_included = _assemble_system_prompt(
        owner=owner,
        report_service=report_service,
        payload=payload,
    )
    gateway = _gateway_for_settings(settings)
    # True SSE exists only on the sidecar CLI path. LAN/cloud get a one-shot chat
    # replayed as a single SSE event so the SPA stream client stays uniform.
    use_sidecar_sse = owner_mode == "sidecar" and transport_kind == "cli"

    async def _proxy_sse() -> AsyncIterator[str]:
        try:
            if use_sidecar_sse:
                async for chunk in gateway.stream_sidecar(
                    connection=payload.connection or owner_cfg.get("default_connection"),
                    model=owner_cfg.get("model"),
                    system_prompt=system_prompt,
                    user_prompt=payload.prompt,
                ):
                    yield chunk
                return

            result = await gateway.chat(
                mode=owner_mode,
                connection=payload.connection or owner_cfg.get("default_connection"),
                model=owner_cfg.get("model"),
                base_url=owner_cfg.get("base_url"),
                api_key=_decrypt_owner_api_key(owner, settings),
                system_prompt=system_prompt,
                user_prompt=payload.prompt,
            )
            yield (
                "data: "
                + json.dumps(
                    {
                        "delta": result.reply,
                        "done": True,
                        "connection": result.connection,
                        "provider": result.provider,
                        "model": result.model,
                    }
                )
                + "\n\n"
            )
        except AITransportError as exc:
            logger.warning("AI stream transport failed for owner_id=%s (status=%s)", owner.id, exc.status_code)
            safe_msg = (
                "Invalid AI connection configuration." if exc.status_code == 400 else "AI transport request failed."
            )
            yield f"data: {json.dumps({'error': safe_msg, 'done': True})}\n\n"
        except httpx.HTTPError as exc:
            logger.warning("AI stream transport failed for owner_id=%s: %s", owner.id, type(exc).__name__)
            yield f"data: {json.dumps({'error': 'Self-hosted AI sidecar unavailable', 'done': True})}\n\n"

    return StreamingResponse(_proxy_sse(), media_type="text/event-stream")
