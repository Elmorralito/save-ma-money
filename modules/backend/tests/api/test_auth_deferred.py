"""Tests for deferred local-auth refresh/logout (no Supabase session store)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_refresh_returns_501_when_local(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "dummy-refresh"})
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
    assert "supabase" in (payload.get("deferred_reason") or "").lower()


def test_logout_returns_501_when_local(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "dummy-refresh", "access_token": "dummy-access"},
    )
    assert response.status_code == 501
    payload = response.json()
    assert "detail" in payload
