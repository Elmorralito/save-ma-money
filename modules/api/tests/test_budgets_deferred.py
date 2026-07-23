"""Tests for deferred budget 501 stubs (JWT required — PPT-044)."""

from __future__ import annotations

from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.main import create_app


def test_budgets_list_requires_auth() -> None:
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    client = TestClient(create_app())
    response = client.get("/api/v1/budgets")
    assert response.status_code == 401


def test_budgets_list_returns_501_when_authenticated() -> None:
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    app = create_app()
    owner = make_user()
    app.dependency_overrides[get_current_owner] = lambda: owner
    client = TestClient(app)
    response = client.get("/api/v1/budgets")
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
    assert payload.get("deferred_reason") == "FR-09 budgets deferred to v4.1"
    app.dependency_overrides.clear()


def test_budgets_create_returns_501_when_authenticated() -> None:
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    app = create_app()
    owner = make_user()
    app.dependency_overrides[get_current_owner] = lambda: owner
    client = TestClient(app)
    response = client.post("/api/v1/budgets", json={})
    assert response.status_code == 501
    app.dependency_overrides.clear()
