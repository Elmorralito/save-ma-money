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
# Force local HS256 for unit tests even when environments/local/.env has supabase Auth.
os.environ["AUTH_PROVIDER"] = "local"
# TestClient is HTTP — Secure cookies are not stored/sent; keep BFF cookies usable in CI
# even when DEBUG=false (CI default) would otherwise imply Secure cookies.
os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ.setdefault("AUTH_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("API_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("HEALTH_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("REDIS_RATE_LIMIT_ENABLED", "false")
# Keep OpenAPI available for contract smoke tests (production gates docs via DOCS_ENABLED).
os.environ.setdefault("DOCS_ENABLED", "true")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://testserver"]')
# TrustedHost is required when DEBUG=false; TestClient uses Host: testserver.
os.environ.setdefault("ALLOWED_HOSTS", '["testserver","localhost","127.0.0.1"]')
# Prefer process env over environments/$PAPITA_ENV/.env for unit tests (live tests set URLs explicitly).
if "DATABASE_URL" not in os.environ and "TEST_DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = ""

from auth_helpers import make_user

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import (
    clear_transaction_templates_service_cache,
    clear_transactions_service_cache,
    get_users_service,
)
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.users.dto import UsersDTO


def _clear_auth_singletons() -> None:
    """Reset Settings cache and AuthSecurityManager after env/provider changes."""
    from papita_txnsapi.core.bff_session import clear_memory_bff_sessions

    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    clear_transactions_service_cache()
    clear_transaction_templates_service_cache()
    clear_memory_bff_sessions()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with cached settings cleared."""
    _clear_auth_singletons()
    return TestClient(create_app())


@pytest.fixture
def users_client() -> tuple[TestClient, MagicMock]:
    """Test client with ``get_users_service`` overridden by a mock."""
    _clear_auth_singletons()
    app = create_app()
    mock_service = MagicMock()
    app.dependency_overrides[get_users_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client() -> tuple[TestClient, UsersDTO]:
    """Test client with authenticated owner dependency."""
    from papita_txnsapi.dependencies.auth import get_current_owner

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    app.dependency_overrides[get_current_owner] = lambda: owner
    test_client = TestClient(app)
    yield test_client, owner
    app.dependency_overrides.clear()


@pytest.fixture
def accounts_client() -> tuple[TestClient, UsersDTO, MagicMock]:
    """Authenticated client with mocked AccountsService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_accounts_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_service = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_accounts_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, owner, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def categories_client() -> tuple[TestClient, UsersDTO, MagicMock]:
    """Authenticated client with mocked CategoriesService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_categories_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_service = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_categories_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, owner, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def transactions_client() -> tuple[TestClient, UsersDTO, MagicMock]:
    """Authenticated client with mocked TransactionsService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_transactions_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_service = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_transactions_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, owner, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def templates_client() -> tuple[TestClient, UsersDTO, MagicMock]:
    """Authenticated client with mocked TransactionTemplatesService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_transaction_templates_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_service = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_transaction_templates_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, owner, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def movements_client() -> tuple[TestClient, UsersDTO, MagicMock, MagicMock]:
    """Authenticated client with mocked TransactionsService and AccountsService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_accounts_service, get_transactions_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_transactions = MagicMock()
    mock_accounts = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_transactions_service] = lambda: mock_transactions
    app.dependency_overrides[get_accounts_service] = lambda: mock_accounts
    test_client = TestClient(app)
    yield test_client, owner, mock_transactions, mock_accounts
    app.dependency_overrides.clear()


@pytest.fixture
def reports_client() -> tuple[TestClient, UsersDTO, MagicMock]:
    """Authenticated client with mocked ReportService."""
    from papita_txnsapi.dependencies.auth import get_current_owner
    from papita_txnsapi.dependencies.services import get_report_service

    _clear_auth_singletons()
    app = create_app()
    owner = make_user()
    mock_service = MagicMock()
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_report_service] = lambda: mock_service
    test_client = TestClient(app)
    yield test_client, owner, mock_service
    app.dependency_overrides.clear()


@pytest.fixture
def fake_redis():
    """In-memory Redis client for unit tests (decode_responses=True)."""
    import fakeredis

    return fakeredis.FakeRedis(decode_responses=True)
