"""Unit tests for the self-hosted AI agent sidecar adapters and FastAPI app."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.domains.ai_agent.adapters import (
    AIAgentError,
    AIAgentRegistry,
    AIResponse,
    CLIAdapter,
    ConnectionKind,
    OllamaAdapter,
    OpenAICompatAdapter,
    _scrubbed_subprocess_env,
    build_adapter_from_env,
    build_registry_from_env,
)
from backend.domains.ai_agent.app import create_sidecar_app


class _FakeAdapter:
    def __init__(
        self,
        *,
        kind: ConnectionKind = "cli",
        provider: str = "cli:claude",
        model: str | None = "claude",
        ready: bool = True,
        reply: str = "hello",
        fail: bool = False,
    ) -> None:
        self._kind = kind
        self._provider = provider
        self._model = model
        self._ready = ready
        self._reply = reply
        self._fail = fail
        self.calls: list[dict[str, str]] = []

    @property
    def connection_kind(self) -> ConnectionKind:
        return self._kind

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str | None:
        return self._model

    async def health(self) -> bool:
        return self._ready

    async def generate(self, *, system_prompt: str, user_prompt: str, model: str | None = None) -> AIResponse:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, "model": model})
        if self._fail:
            raise AIAgentError("adapter boom")
        return AIResponse(reply=self._reply, provider=self.provider_name, model=model or self.model_name)

    async def stream(self, *, system_prompt: str, user_prompt: str, model: str | None = None) -> AsyncIterator[str]:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt, "model": model})
        if self._fail:
            raise AIAgentError("stream boom")
        yield self._reply


def test_scrubbed_subprocess_env_strips_secrets() -> None:
    env = _scrubbed_subprocess_env(
        {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "DATABASE_URL": "postgresql://secret",
            "JWT_SECRET_KEY": "super-secret",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key",
            "GMAIL_REFRESH_TOKEN": "refresh-token",
            "AI_AGENT_SHARED_SECRET": "sidecar-secret",
            "REDIS_URL": "redis://secret",
            "AWS_SECRET_ACCESS_KEY": "aws-secret",
        }
    )
    assert env == {"PATH": "/usr/bin", "HOME": "/home/user"}


def test_cli_adapter_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported AI_CLI_PROVIDER"):
        CLIAdapter(cli_name="bash")


def test_cli_adapter_runs_subprocess_exec_with_scrubbed_env() -> None:
    adapter = CLIAdapter(cli_name="claude", binary_path="/usr/local/bin/claude", timeout_seconds=10.0)
    fake_proc = AsyncMock()
    fake_proc.returncode = 0
    fake_proc.communicate = AsyncMock(return_value=(b"Your net worth is positive.\n", b""))

    with (
        patch("backend.domains.ai_agent.adapters.shutil.which", return_value="/usr/local/bin/claude"),
        patch(
            "backend.domains.ai_agent.adapters.asyncio.create_subprocess_exec",
            return_value=fake_proc,
        ) as mock_exec,
    ):
        assert asyncio.run(adapter.health()) is True
        res = asyncio.run(adapter.generate(system_prompt="System guardrail", user_prompt="How am I doing?"))

    assert res.reply == "Your net worth is positive."
    assert res.provider == "cli:claude"
    call_args = mock_exec.call_args.args
    assert call_args[0] == "/usr/local/bin/claude"
    assert "--tools" in call_args
    assert "" in call_args


def test_ollama_and_openai_compat_adapters() -> None:
    ollama = OllamaAdapter(base_url="http://ollama.local:11434", model="llama3.2")
    mock_ollama_resp = httpx.Response(
        200,
        json={"message": {"content": "Local Ollama answer"}},
        request=httpx.Request("POST", "http://ollama.local:11434/api/chat"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_ollama_resp)):
        res = asyncio.run(ollama.generate(system_prompt="sys", user_prompt="hi"))
    assert res.reply == "Local Ollama answer"
    assert res.provider == "ollama"

    oai = OpenAICompatAdapter(base_url="http://vllm.local:1234/v1", model="qwen")
    mock_oai_resp = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "OpenAI-compat answer"}}]},
        request=httpx.Request("POST", "http://vllm.local:1234/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_oai_resp)):
        oai_res = asyncio.run(oai.generate(system_prompt="sys", user_prompt="hi"))
    assert oai_res.reply == "OpenAI-compat answer"
    assert oai_res.provider == "openai_compat"


def test_build_adapter_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_AGENT_ENABLED_CONNECTIONS", raising=False)
    monkeypatch.setenv("AI_AGENT_BACKEND", "cli")
    monkeypatch.setenv("AI_CLI_PROVIDER", "agy")
    adapter = build_adapter_from_env()
    assert adapter.provider_name == "cli:agy"
    assert adapter.connection_kind == "cli"

    monkeypatch.setenv("AI_AGENT_ENABLED_CONNECTIONS", "ollama,cli:claude,cli:agy,cli:cursor,openai_compat")
    monkeypatch.setenv("AI_AGENT_DEFAULT_CONNECTION", "cli:agy")
    registry = build_registry_from_env()
    assert registry.ids() == ["ollama", "cli:claude", "cli:agy", "cli:cursor", "openai_compat"]
    assert registry.default_id == "cli:agy"
    assert registry.get("ollama").connection_kind == "api"
    assert registry.get("cli:cursor").connection_kind == "cli"

    monkeypatch.setenv("AI_AGENT_ENABLED_CONNECTIONS", "invalid")
    with pytest.raises(ValueError, match="Unknown AI connection"):
        build_registry_from_env()


def test_sidecar_app_supports_both_api_and_cli_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_AGENT_SHARED_SECRET", "top-secret-123")
    api_adapter = _FakeAdapter(kind="api", provider="ollama", model="llama3.2", ready=True, reply="API reply")
    cli_adapter = _FakeAdapter(kind="cli", provider="cli:claude", model="claude", ready=True, reply="CLI reply")
    registry = AIAgentRegistry({"ollama": api_adapter, "cli:claude": cli_adapter}, default_id="ollama")
    client = TestClient(create_sidecar_app(registry=registry))

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["default_connection"] == "ollama"
    assert len(body["connections"]) == 2
    assert {c["id"]: c["kind"] for c in body["connections"]} == {"ollama": "api", "cli:claude": "cli"}

    unauth = client.post("/respond", json={"system_prompt": "sys", "user_prompt": "hi"})
    assert unauth.status_code == 401

    default_ok = client.post(
        "/respond",
        headers={"X-Papita-AI-Secret": "top-secret-123"},
        json={"system_prompt": "sys", "user_prompt": "hi"},
    )
    assert default_ok.status_code == 200
    assert default_ok.json()["reply"] == "API reply"
    assert default_ok.json()["kind"] == "api"

    cli_ok = client.post(
        "/respond",
        headers={"X-Papita-AI-Secret": "top-secret-123"},
        json={"system_prompt": "sys", "user_prompt": "hi", "connection": "cli:claude"},
    )
    assert cli_ok.status_code == 200
    assert cli_ok.json()["reply"] == "CLI reply"
    assert cli_ok.json()["kind"] == "cli"

    bad_conn = client.post(
        "/respond",
        headers={"X-Papita-AI-Secret": "top-secret-123"},
        json={"system_prompt": "sys", "user_prompt": "hi", "connection": "cli:unknown"},
    )
    assert bad_conn.status_code == 400

    stream = client.post(
        "/stream",
        headers={"X-Papita-AI-Secret": "top-secret-123"},
        json={"system_prompt": "sys", "user_prompt": "hi", "connection": "cli:claude"},
    )
    assert stream.status_code == 200
    assert '"delta": "CLI reply"' in stream.text
    assert '"done": true' in stream.text


def test_adapters_error_and_health_paths() -> None:
    missing_cli = CLIAdapter(cli_name="cursor", binary_path="/nonexistent/cursor")
    with patch("backend.domains.ai_agent.adapters.shutil.which", return_value=None):
        assert asyncio.run(missing_cli.health()) is False
        with pytest.raises(AIAgentError, match="not found"):
            asyncio.run(missing_cli.generate(system_prompt="", user_prompt="hi"))

    fail_proc = AsyncMock()
    fail_proc.returncode = 2
    fail_proc.communicate = AsyncMock(return_value=(b"", b"bad flag"))
    with (
        patch("backend.domains.ai_agent.adapters.shutil.which", return_value="/usr/bin/cursor"),
        patch("backend.domains.ai_agent.adapters.asyncio.create_subprocess_exec", return_value=fail_proc),
    ):
        with pytest.raises(AIAgentError, match="exited with code 2"):
            asyncio.run(missing_cli.generate(system_prompt="sys", user_prompt="hi"))

    ollama = OllamaAdapter()
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(return_value=httpx.Response(200, request=httpx.Request("GET", "http://x"))),
    ):
        assert asyncio.run(ollama.health()) is True
    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.ConnectError("down"))):
        assert asyncio.run(ollama.health()) is False
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("down"))):
        with pytest.raises(AIAgentError, match="Ollama request failed"):
            asyncio.run(ollama.generate(system_prompt="sys", user_prompt="hi"))

    oai = OpenAICompatAdapter(api_key="local-key")
    assert oai._headers() == {"Authorization": "Bearer local-key"}
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(return_value=httpx.Response(200, request=httpx.Request("GET", "http://x"))),
    ):
        assert asyncio.run(oai.health()) is True
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("down"))):
        with pytest.raises(AIAgentError, match="OpenAI-compatible request failed"):
            asyncio.run(oai.generate(system_prompt="sys", user_prompt="hi"))

    failing_client = TestClient(create_sidecar_app(adapter=_FakeAdapter(fail=True)))
    assert failing_client.post("/respond", json={"system_prompt": "s", "user_prompt": "hi"}).status_code == 502
    err_stream = failing_client.post("/stream", json={"system_prompt": "s", "user_prompt": "hi"})
    assert '"error": "stream boom"' in err_stream.text
