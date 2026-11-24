"""Self-hosted single-owner AI agent sidecar domain (optional Compose profile ``ai-agent``)."""

from backend.domains.ai_agent.adapters import (
    AIAgentAdapter,
    AIAgentError,
    AIAgentRegistry,
    AIResponse,
    CLIAdapter,
    ConnectionKind,
    OllamaAdapter,
    OpenAICompatAdapter,
    build_adapter_from_env,
    build_registry_from_env,
)

__all__ = [
    "AIAgentAdapter",
    "AIAgentError",
    "AIAgentRegistry",
    "AIResponse",
    "CLIAdapter",
    "ConnectionKind",
    "OllamaAdapter",
    "OpenAICompatAdapter",
    "build_adapter_from_env",
    "build_registry_from_env",
]
