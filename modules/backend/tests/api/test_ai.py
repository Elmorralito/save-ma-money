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
    app.dependency_overrides[get_report_service] = lambda: (report_service or _mock_report_service())
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
