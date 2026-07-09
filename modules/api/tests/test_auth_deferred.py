"""Tests for deferred auth endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_refresh_returns_501(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
    assert payload.get("deferred_reason") == "FR-11 refresh/logout deferred — stateless JWT MVP"


def test_logout_returns_501(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
