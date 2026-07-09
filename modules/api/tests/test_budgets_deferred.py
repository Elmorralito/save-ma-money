"""Tests for deferred budget 501 stubs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.main import create_app


def test_budgets_list_returns_501() -> None:
    get_settings.cache_clear()
    client = TestClient(create_app())
    response = client.get("/api/v1/budgets")
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
    assert payload.get("deferred_reason") == "FR-09 budgets deferred to v4.1"
