"""Unit tests covering AITransportGateway cloud API, built-in LAN, and sidecar paths."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from backend.domains.ai_agent.resilience import RetryPolicy
from backend.domains.ai_agent.transport import AITransportError, AITransportGateway

_NO_RETRY = RetryPolicy(max_attempts=1, base_delay_seconds=0.0, max_delay_seconds=0.0, jitter_ratio=0.0)
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _gateway() -> AITransportGateway:
    return AITransportGateway(
        sidecar_url="http://127.0.0.1:8787",
        sidecar_secret="test-secret",
        qwen_finance_base_url="http://host.docker.internal:11434",
        qwen_finance_model="qwen-finance:7b",
        timeout_seconds=5.0,
        discovery_retry_policy=_NO_RETRY,
        chat_retry_policy=_NO_RETRY,
    )


def _patch_async_client(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)

    class _PatchedClient(_REAL_ASYNC_CLIENT):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.pop("transport", None)
            super().__init__(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _PatchedClient)


def test_discover_cloud_models_for_anthropic_gemini_and_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cloud discovery parses Anthropic, Gemini, and OpenAI catalogs."""

    async def _run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "anthropic" in url:
                assert request.headers["x-api-key"] == "ant-fixture-val"
                return httpx.Response(
                    200,
                    json={"data": [{"id": "claude-3-5-sonnet", "display_name": "Claude Sonnet"}]},
                )
            if "generativelanguage" in url:
                return httpx.Response(
                    200,
                    json={
                        "models": [
                            {
                                "name": "models/gemini-2.5-flash",
                                "displayName": "Gemini 2.5 Flash",
                                "supportedGenerationMethods": ["generateContent"],
                            },
                            {
                                "name": "models/embedding-001",
                                "supportedGenerationMethods": ["embedContent"],
                            },
                        ]
                    },
                )
            return httpx.Response(200, json={"data": [{"id": "gpt-4o-mini"}, {"id": "whisper-1"}]})

        _patch_async_client(monkeypatch, handler)
        gw = _gateway()

        ant = await gw.list_models(mode="api_key", connection="anthropic", api_key="ant-fixture-val")
        assert ant.models[0].id == "claude-3-5-sonnet"

        gem = await gw.list_models(mode="api_key", connection="gemini", api_key="gem-fixture-val")
        assert [m.id for m in gem.models] == ["gemini-2.5-flash"]

        oai = await gw.list_models(mode="api_key", connection="openai", api_key="oai-fixture-val")
        assert [m.id for m in oai.models] == ["gpt-4o-mini"]

    asyncio.run(_run())


def test_discover_cloud_models_errors_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing key raises 400 and upstream 401/500 map to 400/502."""

    async def _run() -> None:
        gw = _gateway()
        with pytest.raises(AITransportError, match="Unsupported direct API provider"):
            await gw.list_models(mode="api_key", connection="unknown_cloud", api_key="k")
        with pytest.raises(AITransportError, match="Provide or save an API key"):
            await gw.list_models(mode="api_key", connection="openai", api_key="")

        def fail_401(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "bad key"}, request=request)

        _patch_async_client(monkeypatch, fail_401)
        with pytest.raises(AITransportError) as exc_401:
            await gw.list_models(mode="api_key", connection="anthropic", api_key="bad")
        assert exc_401.value.status_code == 400

        def fail_net(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down", request=request)

        _patch_async_client(monkeypatch, fail_net)
        with pytest.raises(AITransportError) as exc_net:
            await gw.list_models(mode="api_key", connection="gemini", api_key="k")
        assert exc_net.value.status_code == 502

    asyncio.run(_run())


def test_discover_lan_models_ollama_openai_and_qwen_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Built-in LAN discovery handles Ollama, OpenAI-compat, qwen fallback, and 502 failures."""

    async def _run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url.endswith("/api/tags"):
                return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b-instruct"}]})
            if "/v1/models" in url and "fail-openai" in url:
                return httpx.Response(404, request=request)
            if url.endswith("/v1/models"):
                return httpx.Response(200, json={"data": [{"id": "local-lora-model"}]})
            return httpx.Response(500, request=request)

        _patch_async_client(monkeypatch, handler)
        gw = _gateway()

        ollama_res = await gw.list_models(mode="lan_local", connection="ollama", base_url="http://127.0.0.1:11434")
        assert ollama_res.models[0].id == "qwen2.5:7b-instruct"

        compat_res = await gw.list_models(
            mode="lan_local", connection="openai_compat", base_url="http://127.0.0.1:1234/v1"
        )
        assert compat_res.models[0].id == "local-lora-model"

        qwen_fallback = await gw.list_models(
            mode="lan_local", connection="qwen_finance", base_url="http://fail-openai.local:11434"
        )
        assert qwen_fallback.default_model == "qwen2.5:7b-instruct"

        def down_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        _patch_async_client(monkeypatch, down_handler)
        with pytest.raises(AITransportError) as lan_down:
            await gw.list_models(mode="lan_local", connection="ollama")
        assert lan_down.value.status_code == 502

    asyncio.run(_run())


def test_discover_and_chat_sidecar_and_cloud_and_lan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise sidecar, Anthropic/Gemini/OpenAI chat, and Ollama/OpenAI-compat/Qwen chat."""

    async def _run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/models" in url and "8787" in url:
                return httpx.Response(200, json={"ready": True, "source": "cli", "models": [{"id": "codex-mini"}]})
            if url.endswith("/respond"):
                return httpx.Response(
                    200, json={"reply": "sidecar ok", "connection": "codex", "kind": "cli", "model": "codex-mini"}
                )
            if "anthropic" in url and url.endswith("/v1/messages"):
                return httpx.Response(
                    200, json={"model": "claude-3-5-sonnet", "content": [{"type": "text", "text": "hi ant"}]}
                )
            if "generativelanguage" in url and ":generateContent" in url:
                return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "hi gem"}]}}]})
            if url.endswith("/api/chat"):
                return httpx.Response(200, json={"model": "qwen-fin", "message": {"content": "hi ollama"}})
            if "/chat/completions" in url:
                if "fallback.local" in url:
                    return httpx.Response(404, request=request)
                return httpx.Response(200, json={"model": "gpt-local", "choices": [{"message": {"content": "hi oai"}}]})
            return httpx.Response(400, json={"detail": "bad request"})

        _patch_async_client(monkeypatch, handler)
        gw = _gateway()

        sc_models = await gw.list_models(mode="sidecar", connection="codex")
        assert sc_models.models[0].id == "codex-mini"

        sc_chat = await gw.chat(
            mode="sidecar",
            connection="codex",
            model=None,
            base_url=None,
            api_key=None,
            system_prompt="sys",
            user_prompt="usr",
        )
        assert sc_chat.reply == "sidecar ok"
        assert sc_chat.kind == "cli"

        ant_chat = await gw.chat(
            mode="api_key",
            connection="anthropic",
            api_key="k",
            model="claude-3-5-sonnet",
            base_url=None,
            system_prompt="s",
            user_prompt="u",
        )
        assert ant_chat.reply == "hi ant"

        gem_chat = await gw.chat(
            mode="api_key",
            connection="gemini",
            api_key="k",
            model="gemini-2.5-flash",
            base_url=None,
            system_prompt="s",
            user_prompt="u",
        )
        assert gem_chat.reply == "hi gem"

        oai_chat = await gw.chat(
            mode="api_key",
            connection="openai",
            api_key="k",
            model="gpt-4o-mini",
            base_url=None,
            system_prompt="s",
            user_prompt="u",
        )
        assert oai_chat.reply == "hi oai"

        oll_chat = await gw.chat(
            mode="lan_local",
            connection="ollama",
            model=None,
            base_url="http://127.0.0.1:11434",
            api_key=None,
            system_prompt="s",
            user_prompt="u",
        )
        assert oll_chat.reply == "hi ollama"

        qwen_fb = await gw.chat(
            mode="lan_local",
            connection="qwen_finance",
            model=None,
            base_url="http://fallback.local:11434",
            api_key=None,
            system_prompt="s",
            user_prompt="u",
        )
        assert qwen_fb.reply == "hi ollama"

        def bad_sidecar(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400, content=json.dumps({"detail": "bad conn"}), headers={"content-type": "application/json"}
            )

        _patch_async_client(monkeypatch, bad_sidecar)
        with pytest.raises(AITransportError) as exc_sc:
            await gw.list_models(mode="sidecar", connection="bad")
        assert exc_sc.value.status_code == 400

    asyncio.run(_run())
