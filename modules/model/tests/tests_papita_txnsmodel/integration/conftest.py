"""Shared fixtures for live PostgreSQL integration tests (B0)."""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector

POSTGRES_URL = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
requires_postgres = pytest.mark.skipif(
    not POSTGRES_URL or not str(POSTGRES_URL).startswith("postgresql"),
    reason="DATABASE_URL must point to PostgreSQL for live integration tests",
)


@pytest.fixture(scope="session")
def postgres_connector():
    """Establish a PostgreSQL connection for the integration session."""
    SQLDatabaseConnector.close()
    SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
    yield SQLDatabaseConnector
    SQLDatabaseConnector.close()


@pytest.fixture
def db_session(postgres_connector):
    """Yield a database session and roll back after each test."""
    session = Session(postgres_connector.engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def integration_owner_ids():
    """Stable UUIDs for two integration tenants."""
    return {
        "user_a": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "user_b": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    }


@pytest.fixture
def ensure_integration_users(db_session, integration_owner_ids):
    """Insert two users when missing (rolled back after test)."""
    for key, user_id in integration_owner_ids.items():
        username = f"ppt041_{key}"
        email = f"{username}@example.local"
        db_session.execute(
            text(
                """
                INSERT INTO papita_transactions.users (id, username, email, password, active, created_at, updated_at)
                VALUES (:id, :username, :email, 'hashed', true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": str(user_id), "username": username, "email": email},
        )
    db_session.commit()
    yield
