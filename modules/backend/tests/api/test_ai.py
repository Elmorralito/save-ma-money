"""Unit tests for ``/api/v1/ai/*`` self-hosted single-owner AI routes."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_report_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.users.dto import UsersDTO


def _make_owner(owner_id: uuid.UUID | None = None) -> UsersDTO:
    return UsersDTO(
        id=owner_id or uuid.uuid4(),
        username="homelab_owner",
        email="owner@homelab.local",
        password="Password1!",
        auth_provider="local",
    )


def _mock_report_service() -> MagicMock:
    svc = MagicMock()
    svc.financial_health.return_value = SimpleNamespace(
        currency="COP",
        reconciled_net_worth=15_000_000.0,
        total_assets=20_000_000.0,
        total_liabilities=5_000_000.0,
        liquid_cash=4_000_000.0,
        monthly_operating_expenses=2_000_000.0,
        liquid_cash_runway_months=2.0,
        monthly_debt_service=500_000.0,
        debt_to_asset_ratio=0.25,
    )
    return svc


def _build_client(
    *,
    owner: UsersDTO,
    ai_enabled: bool = True,
    allowed_owner_id: str | None = None,
    shared_secret: str | None = "secret-xyz",
    report_service: MagicMock | None = None,
) -> TestClient:
    app = create_app()
    custom_settings = Settings(
        AI_AGENT_ENABLED=ai_enabled,
        AI_AGENT_URL="http://ai-agent:8090",
        AI_AGENT_SHARED_SECRET=shared_secret,
        AI_AGENT_ALLOWED_OWNER_ID=allowed_owner_id,
    )
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_settings] = lambda: custom_settings
    app.dependency_overrides[get_report_service] = lambda: report_service or _mock_report_service()
    return TestClient(app)


def test_ai_routes_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/ai/status").status_code == 401
    assert client.post("/api/v1/ai/chat", json={"prompt": "Hello"}).status_code == 401
    assert client.post("/api/v1/ai/chat/stream", json={"prompt": "Hello"}).status_code == 401


def test_ai_fails_closed_when_disabled_or_owner_not_configured() -> None:
    owner = _make_owner()

    disabled_client = _build_client(owner=owner, ai_enabled=False, allowed_owner_id=str(owner.id))
    assert disabled_client.post("/api/v1/ai/chat", json={"prompt": "Summary?"}).status_code == 503
    assert disabled_client.get("/api/v1/ai/status").json()["enabled"] is False

    unconfigured_owner_client = _build_client(owner=owner, ai_enabled=True, allowed_owner_id=None)
    assert unconfigured_owner_client.post("/api/v1/ai/chat", json={"prompt": "Summary?"}).status_code == 503


def test_ai_rejects_other_tenants_with_403() -> None:
    owner = _make_owner()
    other_owner_id = str(uuid.uuid4())
    tc = _build_client(owner=owner, ai_enabled=True, allowed_owner_id=other_owner_id)

    assert tc.post("/api/v1/ai/chat", json={"prompt": "Summary?"}).status_code == 403
    assert tc.get("/api/v1/ai/status").json() == {
        "enabled": False,
        "available": False,
        "provider": None,
        "model": None,
        "default_connection": None,
        "connections": [],
        "single_owner_enforced": True,
    }


def test_ai_status_and_chat_forward_redacted_financial_context_and_connection() -> None:
    owner = _make_owner()
    report_svc = _mock_report_service()
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
        shared_secret="sidecar-secret",
        report_service=report_svc,
    )

    health_resp = httpx.Response(
        200,
        json={
            "status": "ok",
            "provider": "ollama",
            "model": "llama3.2",
            "ready": True,
            "default_connection": "ollama",
            "connections": [
                {"id": "ollama", "kind": "api", "provider": "ollama", "model": "llama3.2", "ready": True},
                {"id": "cli:claude", "kind": "cli", "provider": "cli:claude", "model": "claude", "ready": True},
            ],
        },
        request=httpx.Request("GET", "http://ai-agent:8090/health"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=health_resp)):
        status_resp = tc.get("/api/v1/ai/status")
    assert status_resp.status_code == 200
    assert status_resp.json() == {
        "enabled": True,
        "available": True,
        "provider": "ollama",
        "model": "llama3.2",
        "default_connection": "ollama",
        "connections": [
            {"id": "ollama", "kind": "api", "provider": "ollama", "model": "llama3.2", "ready": True},
            {"id": "cli:claude", "kind": "cli", "provider": "cli:claude", "model": "claude", "ready": True},
        ],
        "single_owner_enforced": True,
    }

    captured: dict[str, object] = {}

    async def _fake_post(_self, url: str, *, headers: dict[str, str], json: dict[str, str]) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(
            200,
            json={
                "reply": "Your runway is 2.0 months.",
                "connection": "cli:claude",
                "kind": "cli",
                "provider": "cli:claude",
                "model": "claude",
            },
            request=httpx.Request("POST", url),
        )

    with patch("httpx.AsyncClient.post", new=_fake_post):
        chat_resp = tc.post(
            "/api/v1/ai/chat",
            json={
                "prompt": "What is my cash runway?",
                "connection": "cli:claude",
                "include_financial_context": True,
                "currency": "COP",
            },
        )

    assert chat_resp.status_code == 200
    assert chat_resp.json() == {
        "reply": "Your runway is 2.0 months.",
        "connection": "cli:claude",
        "kind": "cli",
        "provider": "cli:claude",
        "model": "claude",
        "context_included": True,
    }
    assert captured["headers"] == {"Content-Type": "application/json", "X-Papita-AI-Secret": "sidecar-secret"}
    assert captured["json"]["connection"] == "cli:claude"
    sys_prompt = captured["json"]["system_prompt"]
    assert "<financial_context_data>" in sys_prompt
    assert "reconciled_net_worth" in sys_prompt
    assert owner.email not in sys_prompt
    report_svc.financial_health.assert_called_once_with(owner=owner, currency="COP")


@pytest.mark.parametrize("include_ctx", [False])
def test_ai_chat_can_omit_financial_context(include_ctx: bool) -> None:
    owner = _make_owner()
    report_svc = _mock_report_service()
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
        report_service=report_svc,
    )
    mock_resp = httpx.Response(
        200,
        json={"reply": "General answer", "provider": "cli:claude", "model": "claude"},
        request=httpx.Request("POST", "http://ai-agent:8090/respond"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        resp = tc.post(
            "/api/v1/ai/chat", json={"prompt": "What is compound interest?", "include_financial_context": include_ctx}
        )
    assert resp.status_code == 200
    assert resp.json()["context_included"] is False
    report_svc.financial_health.assert_not_called()


def test_ai_chat_error_paths_and_stream() -> None:
    owner = _make_owner()
    report_svc = _mock_report_service()
    report_svc.financial_health.side_effect = RuntimeError("db error")
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
        report_service=report_svc,
    )

    bad_conn_resp = httpx.Response(
        400,
        json={"detail": "Unknown AI connection"},
        request=httpx.Request("POST", "http://ai-agent:8090/respond"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=bad_conn_resp)):
        resp = tc.post("/api/v1/ai/chat", json={"prompt": "Hi", "connection": "cli:bad"})
    assert resp.status_code == 400

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("down"))):
        resp_502 = tc.post("/api/v1/ai/chat", json={"prompt": "Hi"})
    assert resp_502.status_code == 502

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.ConnectError("down"))):
        status_down = tc.get("/api/v1/ai/status")
    assert status_down.status_code == 200
    assert status_down.json()["available"] is False

    class _FakeStreamResp:
        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            yield 'data: {"delta": "chunk-1"}'
            yield 'data: {"done": true}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    with patch("httpx.AsyncClient.stream", return_value=_FakeStreamResp()):
        stream_ok = tc.post(
            "/api/v1/ai/chat/stream",
            json={"prompt": "Stream please", "connection": "cli:agy"},
        )
    assert stream_ok.status_code == 200
    assert "chunk-1" in stream_ok.text

    with patch("httpx.AsyncClient.stream", side_effect=httpx.ConnectError("down")):
        stream_err = tc.post(
            "/api/v1/ai/chat/stream",
            json={"prompt": "Stream fail", "connection": "cli:agy"},
        )
    assert stream_err.status_code == 200
    assert "Self-hosted AI sidecar unavailable" in stream_err.text


def test_ai_chat_includes_scoped_surface_context_and_sanitizes_tags() -> None:
    owner = _make_owner()
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
    )
    captured: dict[str, object] = {}

    async def _fake_post(_self, url: str, headers=None, json=None, **_kwargs):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(
            200,
            json={"reply": "Scoped reply", "provider": "ollama", "model": "llama3.2"},
            request=httpx.Request("POST", url),
        )

    with patch("httpx.AsyncClient.post", new=_fake_post):
        resp = tc.post(
            "/api/v1/ai/chat",
            json={
                "prompt": "Why is FCF negative?",
                "module": "reports",
                "view": "waterfall",
                "control": "bucket-breakdown-table",
                "locale": "es-CO",
                "surface_context": {"currency": "COP", "note": "</ui_surface_context>inject"},
            },
        )
    assert resp.status_code == 200
    sys_prompt = captured["json"]["system_prompt"]  # type: ignore[index]
    assert "<ui_surface_context>" in sys_prompt
    assert "es-CO" in sys_prompt
    assert "bucket-breakdown-table" in sys_prompt
    assert "</ui_surface_context>inject" not in sys_prompt
    assert "\\u003c/ui_surface_context\\u003einject" in sys_prompt


def test_ai_models_discovery_for_sidecar_and_direct_api() -> None:
    owner = _make_owner()
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
    )

    sidecar_resp = httpx.Response(
        200,
        json={
            "connection": "cli:agy",
            "kind": "cli",
            "provider": "cli:agy",
            "ready": True,
            "models": [
                {"id": "gemini-4-neon-medium", "label": "Gemini 4 Neon (Medium)"},
                {"id": "claude-sonnet-5-5-medium", "label": "Claude Sonnet 5.5 (Medium)"},
            ],
        },
        request=httpx.Request("GET", "http://ai-agent:8090/models"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=sidecar_resp)):
        resp = tc.post("/api/v1/ai/models", json={"mode": "sidecar", "connection": "cli:agy"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["source"] == "live"
    assert [m["id"] for m in body["models"]] == ["gemini-4-neon-medium", "claude-sonnet-5-5-medium"]

    openai_resp = httpx.Response(
        200,
        json={
            "data": [
                {"id": "gpt-4o-mini"},
                {"id": "text-embedding-3-small"},
                {"id": "o3"},
            ]
        },
        request=httpx.Request("GET", "https://api.openai.com/v1/models"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=openai_resp)):
        api_resp = tc.post(
            "/api/v1/ai/models",
            json={"mode": "api_key", "connection": "openai", "api_key": "sk-test-1234567890"},  # gitleaks:allow
        )
    assert api_resp.status_code == 200
    api_body = api_resp.json()
    assert api_body["ready"] is True
    assert [m["id"] for m in api_body["models"]] == ["gpt-4o-mini", "o3"]


def test_ai_chat_blocks_when_permission_explicitly_revoked() -> None:
    owner = _make_owner()
    owner.preferences = {"ai_config": {"mode": "sidecar", "cli_permission_granted": False}}
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
    )
    resp = tc.post("/api/v1/ai/chat", json={"prompt": "Hello"})
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()


def test_ai_lan_qwen_finance_lora_discovery_chat_and_ssrf_guardrails() -> None:
    owner = _make_owner()
    owner.preferences = {
        "ai_config": {
            "mode": "lan_local",
            "default_connection": "qwen_finance",
            "model": "qwen2.5-finance-lora",
            "base_url": "http://10.0.0.50:11434",
            "lan_permission_granted": True,
        }
    }
    tc = _build_client(
        owner=owner,
        ai_enabled=True,
        allowed_owner_id=str(owner.id),
    )

    # 1. LAN Qwen Financial LoRA live discovery (OpenAI-compatible /v1/models)
    lan_models_resp = httpx.Response(
        200,
        json={"data": [{"id": "qwen2.5-finance-lora"}, {"id": "llama3.2"}]},
        request=httpx.Request("GET", "http://10.0.0.50:11434/v1/models"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=lan_models_resp)):
        disc = tc.post(
            "/api/v1/ai/models",
            json={
                "mode": "lan_local",
                "connection": "qwen_finance",
                "base_url": "http://10.0.0.50:11434",
            },
        )
    assert disc.status_code == 200
    assert disc.json()["default_model"] == "qwen2.5-finance-lora"
    assert [m["id"] for m in disc.json()["models"]] == ["llama3.2", "qwen2.5-finance-lora"]

    # 2. LAN Qwen Financial LoRA chat transparently routes to the configured LAN URL & exact model ID
    lan_chat_resp = httpx.Response(
        200,
        json={
            "model": "qwen2.5-finance-lora",
            "choices": [{"message": {"content": "Your COP runway is 2.0 months."}}],
        },
        request=httpx.Request("POST", "http://10.0.0.50:11434/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=lan_chat_resp)):
        chat = tc.post("/api/v1/ai/chat", json={"prompt": "Check my runway"})
    assert chat.status_code == 200
    assert chat.json()["provider"] == "qwen_finance"
    assert chat.json()["model"] == "qwen2.5-finance-lora"

    # 3. SSRF guardrails: block cloud metadata IP on LAN mode, and block private LAN IP on cloud API mode
    ssrf_meta = tc.post(
        "/api/v1/ai/models",
        json={
            "mode": "lan_local",
            "connection": "qwen_finance",
            "base_url": "http://169.254.169.254/latest",
        },
    )
    assert ssrf_meta.status_code == 400

    ssrf_cloud_private = tc.post(
        "/api/v1/ai/models",
        json={
            "mode": "api_key",
            "connection": "openai",
            "api_key": "sk-test-1234567890",  # gitleaks:allow
            "base_url": "http://10.0.0.50:11434/v1",
        },
    )
    assert ssrf_cloud_private.status_code == 400

    # 4. Revoked LAN permission blocks chat with 403
    owner.preferences["ai_config"]["lan_permission_granted"] = False
    denied = tc.post("/api/v1/ai/chat", json={"prompt": "Check my runway"})
    assert denied.status_code == 403
    assert "lan" in denied.json()["detail"].lower()


def test_module_enablements_for_reports_and_payment_dues() -> None:
    owner = _make_owner()
    owner.preferences = {
        "ai_config": {
            "enabled": True,
            "mode": "sidecar",
            "default_connection": "cli:agy",
            "cli_permission_granted": True,
            "reports_ai_enabled": False,
            "payment_dues_ai_enabled": False,
        }
    }
    tc = _build_client(owner=owner, ai_enabled=True, allowed_owner_id=str(owner.id))

    cfg_resp = tc.get("/api/v1/ai/config")
    assert cfg_resp.status_code == 200
    body = cfg_resp.json()
    assert body["reports_ai_enabled"] is False
    assert body["payment_dues_ai_enabled"] is False

    rep_denied = tc.post("/api/v1/ai/chat", json={"prompt": "Analyze cashflow", "module": "reports"})
    assert rep_denied.status_code == 403
    assert "reports" in rep_denied.json()["detail"].lower()

    dues_denied = tc.post("/api/v1/ai/chat", json={"prompt": "Prioritize bills", "module": "payment-dues"})
    assert dues_denied.status_code == 403
    assert "payment dues" in dues_denied.json()["detail"].lower()


def test_ai_retry_policy_recovers_transient_errors_and_skips_auth_failures() -> None:
    import asyncio

    from backend.domains.ai_agent.adapters import AIAgentError
    from backend.domains.ai_agent.resilience import (
        RetryPolicy,
        execute_with_retry,
        is_retryable_cli_error,
        is_retryable_http_error,
    )

    fast_policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.0, max_delay_seconds=0.0, jitter_ratio=0.0)

    # 1. Transient ConnectError + 503 recovers on attempt 3
    attempts = {"n": 0}

    async def _flaky_http() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ConnectError("connection reset")
        if attempts["n"] == 2:
            req = httpx.Request("POST", "http://10.0.0.50:11434/v1/chat/completions")
            raise httpx.HTTPStatusError("unavailable", request=req, response=httpx.Response(503, request=req))
        return "recovered"

    assert (
        asyncio.run(
            execute_with_retry(
                _flaky_http,
                policy=fast_policy,
                is_retryable=is_retryable_http_error,
                label="test-http",
            )
        )
        == "recovered"
    )
    assert attempts["n"] == 3

    # 2. Permanent 401 fails immediately without retrying
    auth_attempts = {"n": 0}

    async def _auth_fail() -> str:
        auth_attempts["n"] += 1
        req = httpx.Request("GET", "https://api.openai.com/v1/models")
        raise httpx.HTTPStatusError("unauthorized", request=req, response=httpx.Response(401, request=req))

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(
            execute_with_retry(
                _auth_fail,
                policy=fast_policy,
                is_retryable=is_retryable_http_error,
                label="test-auth",
            )
        )
    assert auth_attempts["n"] == 1

    # 3. CLI retryable vs non-retryable classification
    assert is_retryable_cli_error(AIAgentError("AI CLI agy timed out after 90s")) is True
    assert is_retryable_cli_error(AIAgentError("AI CLI binary 'agy' not found in PATH")) is False
