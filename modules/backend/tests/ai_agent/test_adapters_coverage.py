"""Unit tests covering CLIAdapter, OllamaAdapter, and OpenAICompatAdapter."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from backend.domains.ai_agent.adapters import AIAgentError, CLIAdapter, OllamaAdapter, OpenAICompatAdapter


def test_cli_adapter_models_args_and_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIAdapter builds model args, handles agy models, timeout, exit code, and happy path."""
    with pytest.raises(ValueError, match="Unsupported AI_CLI_PROVIDER"):
        CLIAdapter(cli_name="unsupported")

    cli = CLIAdapter(cli_name="agy", binary_path="/usr/bin/agy", timeout_seconds=1.0)
    assert cli.connection_kind == "cli"
    assert cli.provider_name == "cli:agy"
    assert cli.model_name == "agy"
    assert "-p" in cli._build_args("default")  # noqa: SLF001
    assert "--model" in cli._build_args("gemini-2.5")  # noqa: SLF001

    monkeypatch.setattr(cli, "_resolve_binary", lambda: "/usr/bin/agy")
    assert asyncio.run(cli.health()) is True

    class _FakeProc:
        def __init__(self, rc: int, out: bytes, err: bytes = b"", *, timeout: bool = False) -> None:
            self.returncode = rc
            self._out = out
            self._err = err
            self._timeout = timeout

        async def communicate(self) -> tuple[bytes, bytes]:
            if self._timeout:
                raise TimeoutError()
            return self._out, self._err

        def kill(self) -> None:
            return None

        async def wait(self) -> int:
            return 1

    # agy models discovery
    async def fake_exec_models(*args: Any, **kwargs: Any) -> _FakeProc:
        del args, kwargs
        return _FakeProc(0, b"gemini-2.5-pro\tGemini Pro\ninvalid-line\n")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec_models)
    models = asyncio.run(cli.list_models())
    assert [m.id for m in models] == ["gemini-2.5-pro"]

    # generate + stream happy path
    async def fake_exec_ok(*args: Any, **kwargs: Any) -> _FakeProc:
        del args, kwargs
        return _FakeProc(0, b"hello from cli\n")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec_ok)
    resp = asyncio.run(cli.generate(system_prompt="sys", user_prompt="hi", model="gemini-2.5-pro"))
    assert resp.reply == "hello from cli"

    async def collect_stream() -> list[str]:
        return [chunk async for chunk in cli.stream(system_prompt="", user_prompt="hi")]

    assert asyncio.run(collect_stream()) == ["hello from cli"]

    # non-zero exit (non-retryable)
    async def fake_exec_fail(*args: Any, **kwargs: Any) -> _FakeProc:
        del args, kwargs
        return _FakeProc(2, b"", b"invalid flag")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec_fail)
    with pytest.raises(AIAgentError, match="exited with code 2"):
        asyncio.run(cli.generate(system_prompt="s", user_prompt="u"))

    # missing binary
    monkeypatch.setattr(cli, "_resolve_binary", lambda: None)
    assert asyncio.run(cli.health()) is False
    with pytest.raises(AIAgentError, match="not found in PATH"):
        asyncio.run(cli.generate(system_prompt="s", user_prompt="u"))


def test_ollama_and_openai_compat_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise OllamaAdapter and OpenAICompatAdapter health, models, generate, stream, and errors."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/api/tags"):
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})
        if url.endswith("/api/chat"):
            return httpx.Response(200, json={"message": {"content": "ollama answer"}})
        if url.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "local-lora"}]})
        if url.endswith("/chat/completions"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "compat answer"}}]})
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    class _MockAsyncClient(real_client):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.pop("transport", None)
            super().__init__(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _MockAsyncClient)

    oll = OllamaAdapter(base_url="http://127.0.0.1:11434/", model="qwen2.5:7b")
    assert oll.connection_kind == "api"
    assert oll.provider_name == "ollama"
    assert oll.model_name == "qwen2.5:7b"
    assert asyncio.run(oll.health()) is True
    assert [m.id for m in asyncio.run(oll.list_models())] == ["qwen2.5:7b"]
    assert asyncio.run(oll.generate(system_prompt="s", user_prompt="u")).reply == "ollama answer"

    async def collect_oll() -> list[str]:
        return [c async for c in oll.stream(system_prompt="s", user_prompt="u")]

    assert asyncio.run(collect_oll()) == ["ollama answer"]

    compat = OpenAICompatAdapter(base_url="http://127.0.0.1:1234/v1/", model="local-lora", api_key="tok-1")
    assert compat.connection_kind == "api"
    assert compat.provider_name == "openai_compat"
    assert compat.model_name == "local-lora"
    assert asyncio.run(compat.health()) is True
    assert [m.id for m in asyncio.run(compat.list_models())] == ["local-lora"]
    assert asyncio.run(compat.generate(system_prompt="s", user_prompt="u")).reply == "compat answer"

    async def collect_compat() -> list[str]:
        return [c async for c in compat.stream(system_prompt="s", user_prompt="u")]

    assert asyncio.run(collect_compat()) == ["compat answer"]
