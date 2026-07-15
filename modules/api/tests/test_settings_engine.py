"""Unit tests for PPT-039 pooler-safe engine kwargs on Settings."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from papita_txnsapi.config.settings import (
    Settings,
    get_settings,
    is_supabase_transaction_pooler_url,
    postgres_engine_kwargs,
)
from papita_txnsmodel.database.connector import SQLDatabaseConnector

_JWT = "test-jwt-secret-key-minimum-32-characters"


class TestPoolerUrlDetection:
    """URL classification for B1 transaction pooler."""

    def test_port_6543(self) -> None:
        assert is_supabase_transaction_pooler_url(
            "postgresql+psycopg2://u:p@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        )

    def test_pgbouncer_query(self) -> None:
        assert is_supabase_transaction_pooler_url(
            "postgresql+psycopg2://u:p@db.example.com:5432/postgres?pgbouncer=true"
        )

    def test_direct_5432_is_not_pooler(self) -> None:
        assert not is_supabase_transaction_pooler_url(
            "postgresql+psycopg2://postgres:p@db.ref.supabase.co:5432/postgres?sslmode=require"
        )


class TestPostgresEngineKwargs:
    """Engine option matrix for B0 vs B1."""

    def test_b0_uses_pool_pre_ping_and_size(self) -> None:
        kwargs = postgres_engine_kwargs(
            url="postgresql+psycopg2://papita:x@localhost:5432/papita_transactions",
            pool_size=7,
        )
        assert kwargs == {"pool_pre_ping": True, "pool_size": 7}

    def test_b1_caps_overflow(self) -> None:
        kwargs = postgres_engine_kwargs(
            url="postgresql+psycopg2://u:p@host.pooler.supabase.com:6543/postgres?pgbouncer=true",
            pool_size=5,
        )
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 0


class TestSettingsEstablish:
    """Settings wires pool kwargs into SQLDatabaseConnector.establish."""

    @patch("papita_txnsapi.config.settings.SQLDatabaseConnector.establish")
    @patch("papita_txnsapi.config.settings.configure_logger")
    def test_postgres_url_passes_pool_opts(self, _mock_logger: MagicMock, mock_establish: MagicMock) -> None:
        mock_establish.return_value = SQLDatabaseConnector
        get_settings.cache_clear()
        url = "postgresql+psycopg2://u:p@localhost:5432/db"
        settings = Settings(JWT_SECRET_KEY=_JWT, DATABASE_URL=url, DATABASE_POOL_SIZE=4)
        mock_establish.assert_called_once_with(
            connection=url,
            pool_pre_ping=True,
            pool_size=4,
        )
        assert settings.DATABASE_URL is SQLDatabaseConnector

    @patch("papita_txnsapi.config.settings.SQLDatabaseConnector.establish")
    @patch("papita_txnsapi.config.settings.configure_logger")
    def test_pooler_url_passes_max_overflow_zero(self, _mock_logger: MagicMock, mock_establish: MagicMock) -> None:
        mock_establish.return_value = SQLDatabaseConnector
        get_settings.cache_clear()
        url = "postgresql+psycopg2://u:p@aws-0-x.pooler.supabase.com:6543/postgres?pgbouncer=true"
        Settings(JWT_SECRET_KEY=_JWT, DATABASE_URL=url, DATABASE_POOL_SIZE=5)
        mock_establish.assert_called_once_with(
            connection=url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=0,
        )

    @patch("papita_txnsapi.config.settings.SQLDatabaseConnector.establish")
    @patch("papita_txnsapi.config.settings.configure_logger")
    def test_missing_url_establishes_default_without_pool_kwargs(
        self, _mock_logger: MagicMock, mock_establish: MagicMock
    ) -> None:
        mock_establish.return_value = SQLDatabaseConnector
        get_settings.cache_clear()
        with pytest.warns(UserWarning, match="DATABASE_URL is None"):
            Settings(JWT_SECRET_KEY=_JWT, DATABASE_URL=None)
        mock_establish.assert_called_once_with(connection=None)
