"""Pytest configuration for papita-transactions-api."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
os.environ.setdefault("AUTH_RATE_LIMIT_ENABLED", "false")

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.main import create_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with cached settings cleared."""
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def users_client() -> tuple[TestClient, MagicMock]:
    """Test client with ``get_users_service`` overridden by a mock."""
    get_settings.cache_clear()
    app = create_app()
    mock_service = MagicMock()
    app.dependency_overrides[get_users_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, mock_service
    app.dependency_overrides.clear()
