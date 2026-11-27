"""Unit tests for the owner-scoped User Settings Console API (/api/v1/settings)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_db, get_users_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.users.dto import UsersDTO


def _make_client() -> tuple[TestClient, UsersDTO]:
    owner = UsersDTO(
        id=uuid.uuid4(),
        username="papita_owner",
        email="owner@example.com",
        password="SecurePass1!",
        display_name="David Restrepo",
        auth_provider="local",
        preferences={"base_currency": "COP", "credit_card_cashflow_only": True},
    )

    class _FakeUsersService:
        def update_user_settings(
            self,
            *,
            owner: UsersDTO,
            display_name: str | None = None,
            update_display_name: bool = False,
            phone: str | None = None,
            update_phone: bool = False,
            preferences: dict[str, object] | None = None,
        ) -> UsersDTO:
            if update_display_name:
                owner.display_name = (display_name or "").strip() or None
            if update_phone:
                owner.phone = (phone or "").strip() or None
            if preferences is not None:
                merged = dict(owner.preferences or {})
                merged.update(preferences)
                owner.preferences = merged
            return owner

    app = create_app(
        settings=Settings(
            DEBUG=True,
            AUTH_PROVIDER="local",
            JWT_SECRET_KEY="settings-test-secret-" + uuid.uuid4().hex,
        )
    )
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_users_service] = lambda: _FakeUsersService()
    return TestClient(app), owner


def test_get_patch_and_reset_user_settings() -> None:
    client, _owner = _make_client()

    # GET defaults
    r_get = client.get("/api/v1/settings")
    assert r_get.status_code == 200
    body = r_get.json()
    assert body["email"] == "owner@example.com"
    assert body["preferences"]["base_currency"] == "COP"
    assert body["preferences"]["credit_card_cashflow_only"] is True
    assert "password" not in body

    # PATCH profile & preferences
    r_patch = client.patch(
        "/api/v1/settings",
        json={
            "display_name": "David R.",
            "phone": "+573016663962",
            "preferences": {
                "base_currency": "USD",
                "locale": "en-US",
                "timezone": "America/New_York",
                "date_format": "YYYY-MM-DD",
                "default_page_size": 50,
                "hide_balances_by_default": True,
                "credit_card_cashflow_only": True,
                "auto_refresh_balances": True,
                "fiscal_month_start_day": 15,
                "payment_due_reminder_days": 7,
                "low_runway_months_threshold": 6,
                "high_utilization_pct_threshold": 25,
                "large_transaction_alert_amount": 1500000.0,
                "redact_card_numbers": True,
                "require_dkim_spf_for_email_ingestion": True,
                "session_idle_timeout_minutes": 60,
            },
        },
    )
    assert r_patch.status_code == 200
    updated = r_patch.json()
    assert updated["display_name"] == "David R."
    assert updated["phone"] == "+573016663962"
    assert updated["preferences"]["base_currency"] == "USD"
    assert updated["preferences"]["default_page_size"] == 50
    assert updated["preferences"]["hide_balances_by_default"] is True

    # POST /reset restores defaults
    r_reset = client.post("/api/v1/settings/reset", json={})
    assert r_reset.status_code == 200
    reset_body = r_reset.json()
    assert reset_body["preferences"]["base_currency"] == "COP"
    assert reset_body["preferences"]["hide_balances_by_default"] is False


def test_settings_rejects_unknown_fields_and_invalid_bounds() -> None:
    client, _owner = _make_client()

    r_extra = client.patch("/api/v1/settings", json={"is_admin": True})
    assert r_extra.status_code == 422

    r_bounds = client.patch(
        "/api/v1/settings",
        json={"preferences": {"fiscal_month_start_day": 31}},
    )
    assert r_bounds.status_code == 422
