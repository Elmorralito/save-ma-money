"""Provider-agnostic AI adapters for the self-hosted ``ai-agent`` sidecar.

Supports:
- ``cli``: local headless CLI binaries (``claude``, ``agy``, ``cursor``) with
  scrubbed subprocess environments, ``shell=False``, no filesystem/shell tools,
  and strict timeouts.
- ``ollama``: local Ollama HTTP API (100% local, zero external egress).
- ``openai_compat``: any local OpenAI-compatible HTTP endpoint (vLLM, LM Studio,
  llama.cpp server).
"""

from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

ConnectionKind = Literal["api", "cli"]

_MAX_OUTPUT_BYTES = 65_536
_SCRUBBED_ENV_PREFIXES = (
    "DATABASE_",
    "DB_",
    "JWT_",
    "SUPABASE_",
    "GMAIL_",
    "REDIS_",
    "AI_AGENT_SHARED_SECRET",
    "AWS_",
)

_CLI_SPECS: dict[str, tuple[str, list[str]]] = {
    # Claude Code non-interactive print mode with all local tools disabled.
    "claude": ("claude", ["-p", "--output-format", "text", "--tools", ""]),
    # Antigravity CLI non-interactive single-turn mode.
    "agy": ("agy", ["chat", "--non-interactive"]),
    # Cursor agent CLI non-interactive print mode.
    "cursor": ("cursor", ["agent", "--print"]),
}


class AIAgentError(RuntimeError):
    """Raised when an AI sidecar adapter fails or times out."""


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Normalized reply returned by an AI adapter."""

    reply: str
    provider: str
    model: str | None = None


class AIAgentAdapter(Protocol):
    """Contract implemented by all self-hosted AI sidecar adapters."""

    @property
    def connection_kind(self) -> ConnectionKind:
        """Whether this adapter connects over HTTP API (``api``) or local CLI (``cli``)."""

    @property
    def provider_name(self) -> str:
        """Short provider identifier (e.g. ``cli:claude``, ``ollama``)."""

    @property
    def model_name(self) -> str | None:
        """Configured model label, if applicable."""

    async def health(self) -> bool:
        """Return True when the underlying CLI binary or local model endpoint is ready."""

    async def generate(self, *, system_prompt: str, user_prompt: str) -> AIResponse:
        """Produce a single complete response."""

    def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Yield incremental response text chunks."""


def _scrubbed_subprocess_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a copy of the environment with backend/DB/OAuth secrets removed."""
    source = dict(os.environ if base_env is None else base_env)
    return {
        key: value
        for key, value in source.items()
        if not any(key.upper().startswith(prefix) for prefix in _SCRUBBED_ENV_PREFIXES)
    }


def _compose_cli_prompt(system_prompt: str, user_prompt: str) -> str:
    """Combine system guardrails and user prompt into one bounded text payload."""
    if not system_prompt.strip():
        return user_prompt
    return f"{system_prompt.strip()}\n\nUser request:\n{user_prompt}"


class CLIAdapter:
    """Invoke a pinned local AI CLI (``claude``, ``agy``, ``cursor``) with shell=False."""

    def __init__(
        self,
        *,
        cli_name: str = "claude",
        binary_path: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        normalized = cli_name.strip().lower()
        if normalized not in _CLI_SPECS:
            supported = ", ".join(sorted(_CLI_SPECS))
            raise ValueError(f"Unsupported AI_CLI_PROVIDER={cli_name!r}; expected one of: {supported}")
        default_bin, args = _CLI_SPECS[normalized]
        self._cli_name = normalized
        self._binary = (binary_path or "").strip() or default_bin
        self._args = list(args)
        self._timeout = timeout_seconds

    @property
    def connection_kind(self) -> ConnectionKind:
        return "cli"

    @property
    def provider_name(self) -> str:
        return f"cli:{self._cli_name}"

    @property
    def model_name(self) -> str | None:
        return self._cli_name

    def _resolve_binary(self) -> str | None:
        return shutil.which(self._binary)

    async def health(self) -> bool:
        return self._resolve_binary() is not None

    async def generate(self, *, system_prompt: str, user_prompt: str) -> AIResponse:
        resolved = self._resolve_binary()
        if not resolved:
            raise AIAgentError(f"AI CLI binary {self._binary!r} not found in PATH")

        combined_prompt = _compose_cli_prompt(system_prompt, user_prompt)
        proc = await asyncio.create_subprocess_exec(
            resolved,
            *self._args,
            combined_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_scrubbed_subprocess_env(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AIAgentError(f"AI CLI {self._cli_name} timed out after {self._timeout:.0f}s") from exc

        if proc.returncode != 0:
            err_hint = stderr.decode("utf-8", errors="replace").strip()[:200]
            raise AIAgentError(f"AI CLI {self._cli_name} exited with code {proc.returncode}: {err_hint}")

        reply = stdout[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace").strip()
        return AIResponse(reply=reply, provider=self.provider_name, model=self.model_name)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        response = await self.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        if response.reply:
            yield response.reply


class OllamaAdapter:
    """Local Ollama HTTP adapter (100% local privacy, zero external egress)."""

    def __init__(
        self,
        *,
        base_url: str = "http://host.docker.internal:11434",
        model: str = "llama3.2",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip() or "llama3.2"
        self._timeout = timeout_seconds

    @property
    def connection_kind(self) -> ConnectionKind:
        return "api"

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str | None:
        return self._model

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate(self, *, system_prompt: str, user_prompt: str) -> AIResponse:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise AIAgentError(f"Ollama request failed: {type(exc).__name__}") from exc

        message = data.get("message") or {}
        reply = str(message.get("content") or "").strip()[:_MAX_OUTPUT_BYTES]
        return AIResponse(reply=reply, provider=self.provider_name, model=self._model)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        response = await self.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        if response.reply:
            yield response.reply


class OpenAICompatAdapter:
    """Adapter for local OpenAI-compatible servers (vLLM, LM Studio, llama.cpp)."""

    def __init__(
        self,
        *,
        base_url: str = "http://host.docker.internal:1234/v1",
        model: str = "local-model",
        api_key: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip() or "local-model"
        self._api_key = (api_key or "").strip() or None
        self._timeout = timeout_seconds

    @property
    def connection_kind(self) -> ConnectionKind:
        return "api"

    @property
    def provider_name(self) -> str:
        return "openai_compat"

    @property
    def model_name(self) -> str | None:
        return self._model

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self._base_url}/models", headers=self._headers())
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate(self, *, system_prompt: str, user_prompt: str) -> AIResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise AIAgentError(f"OpenAI-compatible request failed: {type(exc).__name__}") from exc

        choices = data.get("choices") or []
        content = ""
        if choices and isinstance(choices[0], dict):
            content = str((choices[0].get("message") or {}).get("content") or "")
        return AIResponse(reply=content.strip()[:_MAX_OUTPUT_BYTES], provider=self.provider_name, model=self._model)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        response = await self.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        if response.reply:
            yield response.reply


class AIAgentRegistry:
    """Holds one or more enabled AI connections (both API and CLI) for the sidecar."""

    def __init__(self, adapters: dict[str, AIAgentAdapter], *, default_id: str | None = None) -> None:
        if not adapters:
            raise ValueError("AIAgentRegistry requires at least one enabled AI connection")
        self._adapters = dict(adapters)
        resolved_default = default_id if default_id in self._adapters else next(iter(self._adapters))
        self._default_id = resolved_default

    @property
    def default_id(self) -> str:
        return self._default_id

    @property
    def default_adapter(self) -> AIAgentAdapter:
        return self._adapters[self._default_id]

    def ids(self) -> list[str]:
        return list(self._adapters)

    def get(self, connection_id: str | None = None) -> AIAgentAdapter:
        """Resolve a connection by ID, or return the default connection when omitted."""
        if connection_id is None or not connection_id.strip():
            return self.default_adapter
        key = connection_id.strip().lower()
        if key not in self._adapters:
            available = ", ".join(self._adapters)
            raise KeyError(f"Unknown or disabled AI connection {connection_id!r}; enabled: {available}")
        return self._adapters[key]


def _build_single_connection(spec: str, *, timeout: float) -> tuple[str, AIAgentAdapter]:
    """Instantiate one API or CLI adapter from a connection spec string."""
    normalized = spec.strip().lower()
    if normalized == "ollama":
        adapter: AIAgentAdapter = OllamaAdapter(
            base_url=os.environ.get("OLLAMA_BASE_URL") or "http://host.docker.internal:11434",
            model=os.environ.get("OLLAMA_MODEL") or "llama3.2",
            timeout_seconds=timeout,
        )
        return "ollama", adapter
    if normalized == "openai_compat":
        adapter = OpenAICompatAdapter(
            base_url=os.environ.get("AI_OPENAI_BASE_URL") or "http://host.docker.internal:1234/v1",
            model=os.environ.get("AI_OPENAI_MODEL") or "local-model",
            api_key=os.environ.get("AI_OPENAI_API_KEY"),
            timeout_seconds=timeout,
        )
        return "openai_compat", adapter
    if normalized == "cli" or normalized.startswith("cli:"):
        cli_name = normalized.split(":", 1)[1] if ":" in normalized else (os.environ.get("AI_CLI_PROVIDER") or "claude")
        per_cli_bin_env = f"AI_CLI_{cli_name.upper()}_BINARY_PATH"
        binary_path = os.environ.get(per_cli_bin_env) or os.environ.get("AI_CLI_BINARY_PATH")
        adapter = CLIAdapter(cli_name=cli_name, binary_path=binary_path, timeout_seconds=timeout)
        return adapter.provider_name, adapter
    raise ValueError(
        f"Unknown AI connection {spec!r}; expected one of: ollama, openai_compat, cli, cli:claude, cli:agy, cli:cursor"
    )


def build_adapter_from_env() -> AIAgentAdapter:
    """Construct the default AI sidecar adapter from environment variables."""
    return build_registry_from_env().default_adapter


def build_registry_from_env() -> AIAgentRegistry:
    """Build a multi-connection registry supporting simultaneous API and CLI adapters.

    Reads ``AI_AGENT_ENABLED_CONNECTIONS`` (comma-separated, e.g.
    ``ollama,cli:claude,cli:agy``). Falls back to ``AI_AGENT_BACKEND`` (default
    ``ollama``) when unset.
    """
    timeout = float(os.environ.get("AI_AGENT_TIMEOUT_SECONDS") or "90")
    raw_list = (os.environ.get("AI_AGENT_ENABLED_CONNECTIONS") or "").strip()
    if raw_list:
        specs = [part.strip() for part in raw_list.split(",") if part.strip()]
    else:
        backend = (os.environ.get("AI_AGENT_BACKEND") or "ollama").strip()
        specs = [backend]

    adapters: dict[str, AIAgentAdapter] = {}
    for spec in specs:
        conn_id, adapter = _build_single_connection(spec, timeout=timeout)
        adapters[conn_id] = adapter

    default_env = (os.environ.get("AI_AGENT_DEFAULT_CONNECTION") or "").strip().lower() or None
    if default_env == "cli":
        cli_name = (os.environ.get("AI_CLI_PROVIDER") or "claude").strip().lower()
        default_env = f"cli:{cli_name}"
    return AIAgentRegistry(adapters, default_id=default_env)
