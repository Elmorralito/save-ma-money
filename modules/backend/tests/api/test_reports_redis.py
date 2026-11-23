"""Report route Redis cache-aside coverage (Codecov patch gaps)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_report_service
from papita_txnsapi.main import create_app

_SPENDING_PARAMS = {"start_date": "2026-02-01", "end_date": "2026-02-28"}


class TestReportsCache:
    """Cache HIT/MISS headers on report GETs when Redis is enabled."""

    def test_spending_cache_hit(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        mock_service = MagicMock()
        mock_service.spending.return_value = {
            "group_by": "category",
            "expenses": [],
            "expense_total": 0.0,
            "income_total": 0.0,
        }

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_report_service] = lambda: mock_service
            with TestClient(app) as client:
                first = client.get("/api/v1/reports/spending", params=_SPENDING_PARAMS)
                second = client.get("/api/v1/reports/spending", params=_SPENDING_PARAMS)

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.headers.get("X-Cache") == "HIT"
        assert mock_service.spending.call_count == 1

    def test_cash_flow_and_trends_cache_hit(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        mock_service = MagicMock()
        mock_service.cash_flow.return_value = {
            "inflows": 10.0,
            "outflows": 5.0,
            "net": 5.0,
            "portfolio_total": 100.0,
        }
        mock_service.trends.return_value = {
            "period": "month",
            "series": [],
        }

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_report_service] = lambda: mock_service
            with TestClient(app) as client:
                cf1 = client.get("/api/v1/reports/cash-flow", params=_SPENDING_PARAMS)
                cf2 = client.get("/api/v1/reports/cash-flow", params=_SPENDING_PARAMS)
                tr1 = client.get("/api/v1/reports/trends", params={"months": 3})
                tr2 = client.get("/api/v1/reports/trends", params={"months": 3})

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert cf1.status_code == 200 and cf2.headers.get("X-Cache") == "HIT"
        assert tr1.status_code == 200 and tr2.headers.get("X-Cache") == "HIT"
        assert mock_service.cash_flow.call_count == 1
        assert mock_service.trends.call_count == 1

    def test_ppt091_report_routes_cache_hit(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        mock_service = MagicMock()
        mock_service.operating_cashflow.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "waterfall": {"operating_free_cashflow": 100.0},
            "buckets": [],
            "in_transit": {},
            "monthly_series": [],
            "diagnostics": {},
        }
        mock_service.planned_vs_actual.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "summary": {"net_fcf_variance": 10.0},
            "bucket_rollups": [],
            "template_items": [],
            "unplanned_items": [],
            "reconciliation_flags": [],
        }
        mock_service.debt_paydown.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "summary": {"total_debt": 500.0},
            "liabilities": [],
            "liquidity_context": {},
            "excluded_liabilities": None,
        }

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_report_service] = lambda: mock_service
            with TestClient(app) as client:
                wf1 = client.get("/api/v1/reports/operating-cashflow", params=_SPENDING_PARAMS)
                wf2 = client.get("/api/v1/reports/operating-cashflow", params=_SPENDING_PARAMS)
                pv1 = client.get("/api/v1/reports/planned-vs-actual", params=_SPENDING_PARAMS)
                pv2 = client.get("/api/v1/reports/planned-vs-actual", params=_SPENDING_PARAMS)
                dp1 = client.get("/api/v1/reports/debt-paydown")
                dp2 = client.get("/api/v1/reports/debt-paydown")

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert wf1.status_code == 200 and wf2.headers.get("X-Cache") == "HIT"
        assert pv1.status_code == 200 and pv2.headers.get("X-Cache") == "HIT"
        assert dp1.status_code == 200 and dp2.headers.get("X-Cache") == "HIT"
        assert mock_service.operating_cashflow.call_count == 1
        assert mock_service.planned_vs_actual.call_count == 1
        assert mock_service.debt_paydown.call_count == 1
