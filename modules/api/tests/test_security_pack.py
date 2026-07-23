"""Consolidated PPT-044 security regression pack.

Extends (does not replace) auth hardening, health injection, and tenancy suites.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import (
    MAX_BULK_TRANSACTIONS_HARD_CAP,
    MAX_REPORT_WINDOW_DAYS,
    MAX_SEARCH_LENGTH,
    Settings,
    get_settings,
)
from papita_txnsapi.core.rate_limit import get_rate_limiter
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.main import create_app
from papita_txnsapi.schemas.accounts import BankingDetailsSchema
from papita_txnsapi.schemas.query_params import (
    ReportSpendingQuery,
    TransactionListQuery,
    _enforce_report_window,
    get_report_trends_query,
)
from papita_txnsapi.schemas.transactions import TransactionBulkCreate, TransactionCreate


def _clear_singletons() -> None:
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    get_rate_limiter().reset()


@pytest.fixture
def security_client() -> TestClient:
    _clear_singletons()
    return TestClient(create_app())


class TestTransportHardening:
    """P1 transport defaults."""

    def test_security_headers_present(self, security_client: TestClient) -> None:
        response = security_client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("Referrer-Policy") == "no-referrer"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_docs_disabled_when_not_enabled(self) -> None:
        _clear_singletons()
        with pytest.warns(UserWarning, match="DATABASE_URL is None"):
            settings = Settings(
                JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
                DEBUG=False,
                DOCS_ENABLED=False,
                ALLOWED_ORIGINS=["http://localhost:3000"],
                DATABASE_URL=None,
                AUTH_RATE_LIMIT_ENABLED=False,
                API_RATE_LIMIT_ENABLED=False,
                HEALTH_RATE_LIMIT_ENABLED=False,
                REDIS_ENABLED=False,
            )
        app = create_app(settings=settings)
        client = TestClient(app)
        assert client.get("/api/openapi.json").status_code == 404
        assert client.get("/api/docs").status_code == 404


class TestErrorDisclosure:
    """P4 exception hygiene."""

    def test_unhandled_exception_masks_detail(self) -> None:
        # Isolate handlers from BaseHTTPMiddleware (TestClient + anyio ExceptionGroup noise).
        from fastapi import FastAPI

        from papita_txnsapi.core.handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/boom")
        def _boom() -> None:
            raise RuntimeError("secret driver failure psycopg2 boom")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/boom")
        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"] == "Internal server error"
        assert "psycopg" not in response.text.lower()

    def test_driverish_value_error_is_masked(self) -> None:
        _clear_singletons()
        app = create_app()

        @app.get("/api/v1/__bad_value__")
        def _bad() -> None:
            raise ValueError("sqlalchemy.exc.OperationalError: boom")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/__bad_value__")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid request"


class TestInputBounds:
    """P3/P5 schema and report abuse bounds."""

    def test_bulk_create_schema_hard_cap(self) -> None:
        item = {
            "account_id": "00000000-0000-0000-0000-000000000001",
            "category_id": "00000000-0000-0000-0000-000000000002",
            "transaction_type": "expense",
            "amount": 1.0,
            "transaction_date": "2026-01-01",
        }
        with pytest.raises(Exception):
            TransactionBulkCreate(
                transactions=[TransactionCreate.model_validate(item)] * (MAX_BULK_TRANSACTIONS_HARD_CAP + 1)
            )

    def test_write_schema_forbids_extras(self) -> None:
        with pytest.raises(Exception):
            TransactionCreate.model_validate(
                {
                    "account_id": "00000000-0000-0000-0000-000000000001",
                    "category_id": "00000000-0000-0000-0000-000000000002",
                    "transaction_type": "expense",
                    "amount": 1.0,
                    "transaction_date": "2026-01-01",
                    "owner_id": "00000000-0000-0000-0000-000000000099",
                }
            )

    def test_report_window_max_days(self) -> None:
        start = date(2020, 1, 1)
        end = start + timedelta(days=MAX_REPORT_WINDOW_DAYS + 1)
        with pytest.warns(UserWarning, match="DATABASE_URL is None"):
            settings = Settings(
                JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
                DATABASE_URL=None,
                API_REPORT_WINDOW_MAX_DAYS=MAX_REPORT_WINDOW_DAYS,
            )
        with pytest.raises(ValueError, match="report window must be at most"):
            _enforce_report_window(start, end, settings)
        # Ordering still validated on the query model itself.
        with pytest.raises(ValueError, match="on or before"):
            ReportSpendingQuery(start_date=end, end_date=start)

    def test_trends_months_lookback_enforces_max_window(self) -> None:
        """months lookback must not bypass the configured report window max."""
        with pytest.warns(UserWarning, match="DATABASE_URL is None"):
            settings = Settings(
                JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
                DATABASE_URL=None,
                API_REPORT_WINDOW_MAX_DAYS=30,
            )
        with pytest.raises(ValueError, match="report window must be at most 30"):
            get_report_trends_query(months=6, settings=settings)

    def test_transaction_search_max_length(self) -> None:
        with pytest.raises(Exception):
            TransactionListQuery(search="x" * (MAX_SEARCH_LENGTH + 1))

    def test_banking_extension_forbids_extras_and_bounds_strings(self) -> None:
        with pytest.raises(Exception):
            BankingDetailsSchema.model_validate({"entity": "Bank", "extra_field": "nope"})
        with pytest.raises(Exception):
            BankingDetailsSchema.model_validate({"entity": "B" * 300})


class TestHealthOps:
    """P6 health probe hardening."""

    def test_health_live_sets_no_store(self, security_client: TestClient) -> None:
        response = security_client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers.get("Cache-Control") == "no-store"

    def test_health_database_rejects_mutating_methods(self, security_client: TestClient) -> None:
        for method in ("post", "put", "patch", "delete"):
            response = getattr(security_client, method)("/api/v1/health/database")
            assert response.status_code == 405

    def test_health_rate_limit_returns_429(self) -> None:
        _clear_singletons()
        with pytest.warns(UserWarning, match="DATABASE_URL is None"):
            settings = Settings(
                JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
                DEBUG=False,
                DOCS_ENABLED=False,
                ALLOWED_ORIGINS=["http://localhost:3000"],
                DATABASE_URL=None,
                HEALTH_RATE_LIMIT_ENABLED=True,
                HEALTH_RATE_LIMIT_PER_MINUTE=2,
                AUTH_RATE_LIMIT_WINDOW_SECONDS=60,
                AUTH_RATE_LIMIT_ENABLED=False,
                API_RATE_LIMIT_ENABLED=False,
                REDIS_ENABLED=False,
            )
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        client = TestClient(app)
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health").status_code in {200, 503}
        assert client.get("/api/v1/health").status_code in {200, 503}
        blocked = client.get("/api/v1/health")
        assert blocked.status_code == 429
        app.dependency_overrides.clear()


class TestBudgetsAuthParity:
    """Deferred budgets require JWT."""

    def test_budgets_without_jwt_is_401(self, security_client: TestClient) -> None:
        assert security_client.get("/api/v1/budgets").status_code == 401

    def test_budgets_with_jwt_is_501(self) -> None:
        _clear_singletons()
        app = create_app()
        app.dependency_overrides[get_current_owner] = lambda: make_user()
        client = TestClient(app)
        assert client.get("/api/v1/budgets").status_code == 501
        app.dependency_overrides.clear()
