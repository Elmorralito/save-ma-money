"""Report route Redis cache-aside coverage (Codecov patch gaps)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
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
