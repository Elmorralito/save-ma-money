"""PPT-044 client-contract discovery and migration hardening tests."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import MAX_BULK_TRANSACTIONS, Settings, get_settings
from papita_txnsapi.core.client_contract import (
    BREAKING_CHANGES_ID,
    COMPAT_SUNSET_DATE,
    ERROR_BULK_TOO_LARGE,
    ERROR_REPORT_ACCOUNT_NOT_FOUND,
    HEADER_BREAKING_CHANGES,
    HEADER_BULK_MAX,
    HEADER_DEPRECATION,
    HEADER_ERROR_CODE,
    HEADER_REFRESH_BALANCES_DEFAULT,
    HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS,
    HEADER_SUNSET,
)
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_report_service
from papita_txnsapi.main import create_app
from papita_txnsapi.schemas.query_params import _enforce_report_window


def _clear() -> None:
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()


def _settings(**overrides: object) -> Settings:
    base = {
        "JWT_SECRET_KEY": "test-jwt-secret-key-minimum-32-characters",
        "DEBUG": False,
        "DOCS_ENABLED": False,
        "ALLOWED_ORIGINS": ["http://localhost:3000"],
        "ALLOWED_HOSTS": ["testserver", "localhost", "127.0.0.1"],
        "DATABASE_URL": None,
        "AUTH_RATE_LIMIT_ENABLED": False,
        "API_RATE_LIMIT_ENABLED": False,
        "HEALTH_RATE_LIMIT_ENABLED": False,
        "REDIS_ENABLED": False,
    }
    base.update(overrides)
    with pytest.warns(UserWarning, match="DATABASE_URL is None"):
        return Settings(**base)  # type: ignore[arg-type]


class TestClientContractDiscovery:
    """Public probe + response headers."""

    def test_meta_client_contract_is_public(self) -> None:
        _clear()
        client = TestClient(create_app())
        response = client.get("/api/v1/meta/client-contract")
        assert response.status_code == 200
        payload = response.json()
        assert payload["breaking_changes"] == BREAKING_CHANGES_ID
        assert payload["secure_defaults"]["reports_foreign_account_status"] == 404
        assert payload["secure_defaults"]["cash_flow_refresh_balances_default"] is False
        assert payload["effective"]["bulk_max_transactions"] == MAX_BULK_TRANSACTIONS
        assert "report_account_not_found" in payload["error_codes"]
        assert response.headers.get(HEADER_BREAKING_CHANGES) == BREAKING_CHANGES_ID
        assert response.headers.get(HEADER_BULK_MAX) == str(MAX_BULK_TRANSACTIONS)
        assert response.headers.get(HEADER_REFRESH_BALANCES_DEFAULT) == "false"
        assert response.headers.get(HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS) == "404"

    def test_health_live_advertises_contract_headers(self) -> None:
        _clear()
        client = TestClient(create_app())
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers.get(HEADER_BREAKING_CHANGES) == BREAKING_CHANGES_ID


class TestCompatFlags:
    """Temporary legacy behaviors emit Deprecation/Sunset."""

    def test_legacy_report_account_400_compat(self) -> None:
        _clear()
        settings = _settings(API_COMPAT_LEGACY_REPORT_ACCOUNT_400=True)
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        owner = make_user()
        mock_service = MagicMock()
        mock_service.spending.side_effect = ValueError("Account not found for tenant.")
        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_report_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get(
            "/api/v1/reports/spending",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert response.status_code == 400
        assert response.headers.get(HEADER_ERROR_CODE) == ERROR_REPORT_ACCOUNT_NOT_FOUND
        assert response.headers.get(HEADER_DEPRECATION) == "true"
        assert response.headers.get(HEADER_SUNSET) == COMPAT_SUNSET_DATE
        app.dependency_overrides.clear()

    def test_secure_default_report_account_404(self) -> None:
        _clear()
        app = create_app()
        owner = make_user()
        mock_service = MagicMock()
        mock_service.spending.side_effect = ValueError("Account not found for tenant.")
        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_report_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get(
            "/api/v1/reports/spending",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert response.status_code == 404
        assert response.headers.get(HEADER_ERROR_CODE) == ERROR_REPORT_ACCOUNT_NOT_FOUND
        assert HEADER_DEPRECATION not in response.headers
        app.dependency_overrides.clear()

    def test_legacy_refresh_balances_default_compat(self) -> None:
        _clear()
        settings = _settings(API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE=True)
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        owner = make_user()
        mock_service = MagicMock()
        mock_service.cash_flow.return_value = {
            "inflows": 0.0,
            "outflows": 0.0,
            "net": 0.0,
            "portfolio_total": 0.0,
        }
        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_report_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get(
            "/api/v1/reports/cash-flow",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert response.status_code == 200
        assert mock_service.cash_flow.call_args.kwargs["refresh_balances"] is True
        assert response.headers.get(HEADER_DEPRECATION) == "true"
        assert response.headers.get(HEADER_REFRESH_BALANCES_DEFAULT) == "true"
        app.dependency_overrides.clear()


class TestBulkAndWindowBounds:
    """Settings-backed limits with stable error codes."""

    def test_bulk_router_enforces_settings_max(self) -> None:
        _clear()
        settings = _settings(API_BULK_MAX_TRANSACTIONS=2)
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_current_owner] = lambda: make_user()
        client = TestClient(app)
        item = {
            "account_id": "00000000-0000-0000-0000-000000000001",
            "category_id": "00000000-0000-0000-0000-000000000002",
            "transaction_type": "expense",
            "amount": 1.0,
            "transaction_date": "2026-01-01",
        }
        response = client.post("/api/v1/transactions/bulk", json={"transactions": [item, item, item]})
        assert response.status_code == 422
        assert response.headers.get(HEADER_ERROR_CODE) == ERROR_BULK_TOO_LARGE
        assert "at most 2" in response.json()["detail"]
        app.dependency_overrides.clear()

    def test_report_window_uses_settings_max(self) -> None:
        settings = _settings(API_REPORT_WINDOW_MAX_DAYS=30)
        start = date(2026, 1, 1)
        end = start + timedelta(days=31)
        with pytest.raises(ValueError, match="report window must be at most 30"):
            _enforce_report_window(start, end, settings)
