"""Transparent AI transport gateway unifying CLI, LAN/local models, and cloud APIs.

Provides a single provider-agnostic interface used by ``papita_txnsapi.routers.v1.ai``
so route handlers stay thin and never branch on provider-specific HTTP wire formats.
Supports:
- **Headless CLIs** (``cli:agy``, ``cli:claude``, ``cli:codex``, ``cli:cursor``) via sidecar
- **LAN / Local models** (``qwen_finance`` built-in Qwen Financial LoRA, ``ollama``, ``openai_compat``)
- **Direct Cloud APIs** (``openai``, ``anthropic``, ``gemini``) with Fernet-encrypted owner keys
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from backend.domains.ai_agent.adapters import (
    AIAgentError,
    AIModelInfo,
    AIResponse,
    ConnectionKind,
)
from backend.domains.ai_agent.guardrails import (
    AIGuardrailError,
    TransportKind,
    validate_endpoint_url,
)
from backend.domains.ai_agent.resilience import (
    CHAT_RETRY_POLICY,
    DISCOVERY_RETRY_POLICY,
    RetryPolicy,
    execute_with_retry,
    is_retryable_http_error,
)

SHARED_SECRET_HEADER = "X-Papita-AI-Secret"

CLOUD_API_PROVIDERS = frozenset({"openai", "anthropic", "gemini"})
LAN_LOCAL_PROVIDERS = frozenset({"qwen_finance", "ollama", "openai_compat"})
DIRECT_HTTP_PROVIDERS = CLOUD_API_PROVIDERS | frozenset({"openai_compat"})

DEFAULT_PROVIDER_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.5-flash",
    "openai_compat": "local-model",
    "qwen_finance": "qwen-finance-lora",
    "ollama": "llama3.2",
}


@dataclass(frozen=True, slots=True)
class TransportResult:
    """Normalized non-streaming reply returned by ``AITransportGateway``."""

    reply: str
    connection: str
    kind: ConnectionKind
    transport_kind: TransportKind
    provider: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class ModelDiscoveryResult:
    """Normalized model-discovery payload returned by ``AITransportGateway``."""

    connection: str
    ready: bool
    source: Literal["live", "curated"]
    models: list[AIModelInfo]
    default_model: str | None = None


class AITransportError(AIAgentError):
    """Normalized transport failure with HTTP status mapping for API routers."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def classify_transport(mode: str, connection: str) -> TransportKind:
    """Resolve the canonical ``TransportKind`` for a mode + connection ID pair."""
    conn = connection.strip().lower()
    if conn in CLOUD_API_PROVIDERS or (mode == "api_key" and conn == "openai_compat"):
        return "cloud_api"
    if mode == "lan_local" or conn in LAN_LOCAL_PROVIDERS:
        return "lan_local"
    return "cli"


def _sidecar_headers(shared_secret: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    secret = (shared_secret or "").strip()
    if secret:
        headers[SHARED_SECRET_HEADER] = secret
    return headers


async def _fetch_openai_style_models(
    *,
    root_url: str,
    api_key: str | None,
    filter_openai_chat: bool,
    timeout: float,
) -> list[AIModelInfo]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(f"{root_url}/models", headers=headers)
        resp.raise_for_status()
        data = resp.json()
    out: list[AIModelInfo] = []
    for item in data.get("data") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        mid = item["id"].strip()
        if not mid:
            continue
        if filter_openai_chat and not (
            mid.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-"))
            and "embedding" not in mid
            and "whisper" not in mid
            and "tts" not in mid
            and "dall-e" not in mid
            and "audio" not in mid
            and "realtime" not in mid
        ):
            continue
        out.append(AIModelInfo(id=mid, label=mid))
    out.sort(key=lambda m: m.id)
    return out


async def _fetch_ollama_style_models(*, root_url: str, timeout: float) -> list[AIModelInfo]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(f"{root_url}/api/tags")
        resp.raise_for_status()
        data = resp.json()
    out: list[AIModelInfo] = []
    for item in data.get("models") or []:
        if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip():
            name = item["name"].strip()
            out.append(AIModelInfo(id=name, label=name))
    return out


async def _call_openai_style_chat(
    *,
    root_url: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> tuple[str, str]:
    headers: dict[str, str] = {"content-type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{root_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    reply = str(((choices[0].get("message") or {}).get("content") or "")) if choices else ""
    return reply.strip(), str(data.get("model") or model)


async def _call_ollama_style_chat(
    *,
    root_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{root_url}/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    message = data.get("message") or {}
    return str(message.get("content") or "").strip(), str(data.get("model") or model)


class AITransportGateway:
    """Unified transport facade over sidecar CLIs, LAN/local models, and direct cloud APIs."""

    def __init__(
        self,
        *,
        sidecar_url: str,
        sidecar_secret: str | None = None,
        qwen_finance_base_url: str | None = None,
        qwen_finance_model: str | None = None,
        timeout_seconds: float = 90.0,
        discovery_retry_policy: RetryPolicy = DISCOVERY_RETRY_POLICY,
        chat_retry_policy: RetryPolicy = CHAT_RETRY_POLICY,
    ) -> None:
        self._sidecar_url = sidecar_url.rstrip("/")
        self._sidecar_secret = sidecar_secret
        self._qwen_base_url = (qwen_finance_base_url or "").strip().rstrip("/") or None
        self._qwen_model = (qwen_finance_model or "").strip() or DEFAULT_PROVIDER_MODELS["qwen_finance"]
        self._timeout = timeout_seconds
        self._discovery_retry = discovery_retry_policy
        self._chat_retry = chat_retry_policy

    def _resolve_lan_url(self, connection: str, base_url: str | None) -> str:
        candidate = (base_url or "").strip()
        if not candidate:
            if connection == "qwen_finance":
                candidate = self._qwen_base_url or ""
            elif connection == "ollama":
                candidate = "http://host.docker.internal:11434"
            elif connection == "openai_compat":
                candidate = "http://host.docker.internal:1234/v1"
        if not candidate:
            raise AITransportError(
                f"Configure a LAN endpoint URL for {connection} in Settings → AI & LLM or QWEN_FINANCE_BASE_URL.",
                status_code=400,
            )
        try:
            return validate_endpoint_url(candidate, allow_private_lan=True)
        except AIGuardrailError as exc:
            raise AITransportError(str(exc), status_code=400) from exc

    def _resolve_cloud_url(self, provider: str, base_url: str | None) -> str:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "gemini": "https://generativelanguage.googleapis.com",
            "openai_compat": "http://host.docker.internal:1234/v1",
        }
        candidate = (base_url or "").strip() or defaults.get(provider, "")
        try:
            return validate_endpoint_url(candidate, allow_private_lan=(provider == "openai_compat"))
        except AIGuardrailError as exc:
            raise AITransportError(str(exc), status_code=400) from exc

    async def list_models(
        self,
        *,
        mode: Literal["sidecar", "lan_local", "api_key"],
        connection: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ModelDiscoveryResult:
        """Discover exact selectable model IDs transparently across CLI, LAN, or cloud API."""
        conn = connection.strip().lower()

        if mode == "api_key" or conn in CLOUD_API_PROVIDERS:
            return await self._discover_cloud_models(conn, base_url=base_url, api_key=api_key)

        if mode == "lan_local" or conn == "qwen_finance":
            return await self._discover_lan_models(conn, base_url=base_url, api_key=api_key)

        return await self._discover_sidecar_models(conn)

    async def _discover_cloud_models(
        self,
        provider: str,
        *,
        base_url: str | None,
        api_key: str | None,
    ) -> ModelDiscoveryResult:
        if provider not in DIRECT_HTTP_PROVIDERS:
            raise AITransportError(f"Unsupported direct API provider {provider!r}", status_code=400)
        key = (api_key or "").strip()
        if not key and provider != "openai_compat":
            raise AITransportError(
                f"Provide or save an API key for {provider} before connecting.",
                status_code=400,
            )
        root = self._resolve_cloud_url(provider, base_url)

        async def _do_discover() -> list[AIModelInfo]:
            if provider == "anthropic":
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{root}/v1/models",
                        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                return [
                    AIModelInfo(
                        id=item["id"].strip(),
                        label=str(item.get("display_name") or item["id"]).strip(),
                    )
                    for item in (data.get("data") or [])
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip()
                ]
            if provider == "gemini":
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(f"{root}/v1beta/models", headers={"x-goog-api-key": key})
                    resp.raise_for_status()
                    data = resp.json()
                found: list[AIModelInfo] = []
                for item in data.get("models") or []:
                    if not isinstance(item, dict):
                        continue
                    methods = item.get("supportedGenerationMethods") or []
                    if methods and "generateContent" not in methods:
                        continue
                    mid = str(item.get("name") or "").strip().removeprefix("models/")
                    if mid:
                        found.append(AIModelInfo(id=mid, label=str(item.get("displayName") or mid).strip()))
                return found
            return await _fetch_openai_style_models(
                root_url=root,
                api_key=key or None,
                filter_openai_chat=(provider == "openai"),
                timeout=15.0,
            )

        try:
            models = await execute_with_retry(
                _do_discover,
                policy=self._discovery_retry,
                is_retryable=is_retryable_http_error,
                label=f"cloud-models:{provider}",
            )
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            raise AITransportError(
                f"Provider {provider} rejected model discovery (HTTP {code}). Verify API key and permissions.",
                status_code=400 if code in {401, 403} else 502,
            ) from exc
        except httpx.HTTPError as exc:
            raise AITransportError(
                f"Could not reach {provider} model catalog: {type(exc).__name__}",
                status_code=502,
            ) from exc

        default_model = DEFAULT_PROVIDER_MODELS.get(provider)
        if models and not any(m.id == default_model for m in models):
            default_model = models[0].id
        return ModelDiscoveryResult(
            connection=provider,
            ready=True,
            source="live",
            models=models,
            default_model=default_model,
        )

    async def _discover_lan_models(
        self,
        connection: str,
        *,
        base_url: str | None,
        api_key: str | None,
    ) -> ModelDiscoveryResult:
        """Discover models from a LAN server (Qwen Financial LoRA, Ollama, or OpenAI-compat)."""
        root = self._resolve_lan_url(connection, base_url)
        key = (api_key or "").strip() or None
        models: list[AIModelInfo] = []
        last_err: Exception | None = None

        if connection == "ollama":
            try:
                models = await execute_with_retry(
                    lambda: _fetch_ollama_style_models(root_url=root, timeout=10.0),
                    policy=self._discovery_retry,
                    is_retryable=is_retryable_http_error,
                    label="builtin-models:ollama",
                )
            except httpx.HTTPError as exc:
                last_err = exc
        elif connection == "openai_compat":
            try:
                models = await execute_with_retry(
                    lambda: _fetch_openai_style_models(
                        root_url=root, api_key=key, filter_openai_chat=False, timeout=10.0
                    ),
                    policy=self._discovery_retry,
                    is_retryable=is_retryable_http_error,
                    label="builtin-models:openai_compat",
                )
            except httpx.HTTPError as exc:
                last_err = exc
        else:
            # qwen_finance: auto-probe OpenAI-compatible (/v1/models or /models) then Ollama (/api/tags)
            openai_root = root if root.endswith("/v1") else f"{root}/v1"
            for probe_label, probe in (
                (
                    "builtin-models:qwen_finance:openai",
                    lambda: _fetch_openai_style_models(
                        root_url=openai_root, api_key=key, filter_openai_chat=False, timeout=8.0
                    ),
                ),
                (
                    "builtin-models:qwen_finance:ollama",
                    lambda: _fetch_ollama_style_models(root_url=root.removesuffix("/v1"), timeout=8.0),
                ),
            ):
                try:
                    models = await execute_with_retry(
                        probe,
                        policy=self._discovery_retry,
                        is_retryable=is_retryable_http_error,
                        label=probe_label,
                    )
                    last_err = None
                    break
                except httpx.HTTPError as exc:
                    last_err = exc

        if last_err is not None and not models:
            raise AITransportError(
                f"Could not reach LAN model server {connection} at {root}: {type(last_err).__name__}",
                status_code=502,
            ) from last_err

        default_model = self._qwen_model if connection == "qwen_finance" else DEFAULT_PROVIDER_MODELS.get(connection)
        if models and not any(m.id == default_model for m in models):
            # Prefer a Qwen/finance model ID when discovering on qwen_finance
            qwen_match = next(
                (m.id for m in models if "qwen" in m.id.lower() or "fin" in m.id.lower() or "lora" in m.id.lower()),
                models[0].id,
            )
            default_model = qwen_match if connection == "qwen_finance" else models[0].id
        return ModelDiscoveryResult(
            connection=connection,
            ready=True,
            source="live",
            models=models,
            default_model=default_model,
        )

    async def _discover_sidecar_models(self, connection: str) -> ModelDiscoveryResult:
        async def _do_sidecar_models() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self._sidecar_url}/models",
                    params={"connection": connection},
                    headers=_sidecar_headers(self._sidecar_secret),
                )
                if resp.status_code == 400:
                    detail = resp.json().get("detail", "Invalid AI connection")
                    raise AITransportError(detail, status_code=400)
                resp.raise_for_status()
                return dict(resp.json())

        try:
            data = await execute_with_retry(
                _do_sidecar_models,
                policy=self._discovery_retry,
                is_retryable=is_retryable_http_error,
                label=f"sidecar-models:{connection}",
            )
        except AITransportError:
            raise
        except httpx.HTTPError as exc:
            raise AITransportError(
                "Self-hosted AI sidecar unavailable for model discovery",
                status_code=502,
            ) from exc

        models = [
            AIModelInfo(id=str(item["id"]), label=str(item.get("label") or item["id"]))
            for item in (data.get("models") or [])
            if isinstance(item, dict) and item.get("id")
        ]
        ready = bool(data.get("ready"))
        conn_out = str(data.get("connection") or connection)
        source: Literal["live", "curated"] = (
            "live" if conn_out in {"cli:agy", "ollama", "openai_compat", "qwen_finance"} and models else "curated"
        )
        return ModelDiscoveryResult(
            connection=conn_out,
            ready=ready,
            source=source,
            models=models,
            default_model=models[0].id if models else None,
        )

    async def chat(
        self,
        *,
        mode: str,
        connection: str | None,
        model: str | None,
        base_url: str | None,
        api_key: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> TransportResult:
        """Execute a single guarded prompt across CLI, LAN/local model, or cloud API."""
        conn = (connection or "").strip().lower()
        transport_kind = classify_transport(mode, conn)

        if mode == "api_key" and conn in DIRECT_HTTP_PROVIDERS:
            return await self._chat_cloud_api(
                provider=conn,
                model=model,
                base_url=base_url,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        if mode == "lan_local" or conn == "qwen_finance":
            return await self._chat_lan_local(
                connection=conn or "qwen_finance",
                model=model,
                base_url=base_url,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        return await self._chat_sidecar(
            connection=conn or None,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            transport_kind=transport_kind,
        )

    async def _chat_cloud_api(
        self,
        *,
        provider: str,
        model: str | None,
        base_url: str | None,
        api_key: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> TransportResult:
        key = (api_key or "").strip()
        if not key and provider != "openai_compat":
            raise AITransportError(
                f"API key not configured for {provider}. Save your key in Settings → AI & LLM.",
                status_code=400,
            )
        root = self._resolve_cloud_url(provider, base_url)
        resolved_model = (model or "").strip() or DEFAULT_PROVIDER_MODELS.get(provider, "gpt-4o-mini")

        async def _do_cloud_chat() -> tuple[str, str]:
            if provider == "anthropic":
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{root}/v1/messages",
                        headers={
                            "x-api-key": key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": resolved_model,
                            "max_tokens": 1024,
                            "system": system_prompt,
                            "messages": [{"role": "user", "content": user_prompt}],
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                blocks = data.get("content") or []
                text = "".join(
                    b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
                return text, str(data.get("model") or resolved_model)
            if provider == "gemini":
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{root}/v1beta/models/{resolved_model}:generateContent",
                        headers={"x-goog-api-key": key, "content-type": "application/json"},
                        json={
                            "system_instruction": {"parts": [{"text": system_prompt}]},
                            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                candidates = data.get("candidates") or []
                parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
                text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
                return text, resolved_model
            return await _call_openai_style_chat(
                root_url=root,
                api_key=key or None,
                model=resolved_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=self._timeout,
            )

        try:
            reply, out_model = await execute_with_retry(
                _do_cloud_chat,
                policy=self._chat_retry,
                is_retryable=is_retryable_http_error,
                label=f"cloud-chat:{provider}",
            )
        except httpx.HTTPError as exc:
            raise AITransportError(
                f"Direct LLM provider ({provider}) request failed",
                status_code=502,
            ) from exc

        return TransportResult(
            reply=reply,
            connection=provider,
            kind="api",
            transport_kind="cloud_api",
            provider=provider,
            model=out_model,
        )

    async def _chat_lan_local(
        self,
        *,
        connection: str,
        model: str | None,
        base_url: str | None,
        api_key: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> TransportResult:
        root = self._resolve_lan_url(connection, base_url)
        target_model = (model or "").strip() or (
            self._qwen_model if connection == "qwen_finance" else DEFAULT_PROVIDER_MODELS.get(connection, "llama3.2")
        )
        key = (api_key or "").strip() or None
        try:
            if connection == "ollama":
                reply, out_model = await execute_with_retry(
                    lambda: _call_ollama_style_chat(
                        root_url=root,
                        model=target_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        timeout=self._timeout,
                    ),
                    policy=self._chat_retry,
                    is_retryable=is_retryable_http_error,
                    label="builtin-chat:ollama",
                )
            elif connection == "openai_compat":
                reply, out_model = await execute_with_retry(
                    lambda: _call_openai_style_chat(
                        root_url=root,
                        api_key=key,
                        model=target_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        timeout=self._timeout,
                    ),
                    policy=self._chat_retry,
                    is_retryable=is_retryable_http_error,
                    label="builtin-chat:openai_compat",
                )
            else:
                # qwen_finance: try OpenAI-compatible (/v1/chat/completions) first, then Ollama (/api/chat)
                openai_root = root if root.endswith("/v1") else f"{root}/v1"
                try:
                    reply, out_model = await execute_with_retry(
                        lambda: _call_openai_style_chat(
                            root_url=openai_root,
                            api_key=key,
                            model=target_model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            timeout=self._timeout,
                        ),
                        policy=self._chat_retry,
                        is_retryable=is_retryable_http_error,
                        label="builtin-chat:qwen_finance:openai",
                    )
                except httpx.HTTPError:
                    reply, out_model = await execute_with_retry(
                        lambda: _call_ollama_style_chat(
                            root_url=root.removesuffix("/v1"),
                            model=target_model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            timeout=self._timeout,
                        ),
                        policy=self._chat_retry,
                        is_retryable=is_retryable_http_error,
                        label="builtin-chat:qwen_finance:ollama",
                    )
        except httpx.HTTPError as exc:
            raise AITransportError(
                f"LAN model server ({connection}) request failed",
                status_code=502,
            ) from exc

        return TransportResult(
            reply=reply,
            connection=connection,
            kind="api",
            transport_kind="lan_local",
            provider=connection,
            model=out_model,
        )

    async def _chat_sidecar(
        self,
        *,
        connection: str | None,
        model: str | None,
        system_prompt: str,
        user_prompt: str,
        transport_kind: TransportKind,
    ) -> TransportResult:
        body: dict[str, Any] = {"system_prompt": system_prompt, "user_prompt": user_prompt}
        if connection:
            body["connection"] = connection
        if model and model.strip():
            body["model"] = model.strip()

        async def _do_sidecar_chat() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._sidecar_url}/respond",
                    headers=_sidecar_headers(self._sidecar_secret),
                    json=body,
                )
                if resp.status_code == 400:
                    detail = resp.json().get("detail", "Invalid AI connection")
                    raise AITransportError(detail, status_code=400)
                resp.raise_for_status()
                return dict(resp.json())

        try:
            data = await execute_with_retry(
                _do_sidecar_chat,
                policy=self._chat_retry,
                is_retryable=is_retryable_http_error,
                label=f"sidecar-chat:{connection or 'default'}",
            )
        except AITransportError:
            raise
        except httpx.HTTPError as exc:
            raise AITransportError("Self-hosted AI sidecar unavailable", status_code=502) from exc

        raw_kind = data.get("kind")
        kind: ConnectionKind = "cli" if raw_kind == "cli" else "api"
        return TransportResult(
            reply=str(data.get("reply") or ""),
            connection=str(data.get("connection") or connection or "sidecar"),
            kind=kind,
            transport_kind=transport_kind,
            provider=str(data.get("provider") or "unknown"),
            model=data.get("model"),
        )

    async def stream_sidecar(
        self,
        *,
        connection: str | None,
        model: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """Proxy SSE delta chunks from the sidecar with pre-stream connection retries."""
        body: dict[str, Any] = {"system_prompt": system_prompt, "user_prompt": user_prompt}
        if connection:
            body["connection"] = connection
        if model and model.strip():
            body["model"] = model.strip()
        attempts = max(1, self._chat_retry.max_attempts)
        for attempt in range(1, attempts + 1):
            yielded_any = False
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self._sidecar_url}/stream",
                        headers=_sidecar_headers(self._sidecar_secret),
                        json=body,
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if line:
                                yielded_any = True
                                yield f"{line}\n\n"
                return
            except httpx.HTTPError as exc:
                if yielded_any or attempt >= attempts or not is_retryable_http_error(exc):
                    raise
                delay = self._chat_retry.compute_delay(attempt)
                await asyncio.sleep(delay)


__all__ = [
    "AIModelInfo",
    "AIResponse",
    "AITransportError",
    "AITransportGateway",
    "CLOUD_API_PROVIDERS",
    "DEFAULT_PROVIDER_MODELS",
    "DIRECT_HTTP_PROVIDERS",
    "LAN_LOCAL_PROVIDERS",
    "ModelDiscoveryResult",
    "SHARED_SECRET_HEADER",
    "TransportResult",
    "classify_transport",
]
