"""Opt-in Supabase Auth smoke (PPT-039).

Runs when ``AUTH_PROVIDER=supabase`` and ``SUPABASE_URL`` / ``SUPABASE_ANON_KEY``
are set against a live API+DB (skips otherwise so CI stays green without secrets).

Shell one-liner / loud fail: ``make auth-smoke``.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.main import create_app
from papita_txnsmodel.services.users import UsersService

_VALID_PASSWORD = "SecurePass1!"


def _auth_smoke_ready() -> bool:
    return (
        os.environ.get("AUTH_PROVIDER", "").strip() == "supabase"
        and bool(os.environ.get("SUPABASE_URL", "").strip())
        and bool(os.environ.get("SUPABASE_ANON_KEY", "").strip())
        and bool(os.environ.get("DATABASE_URL", "").strip())
    )


requires_supabase_auth = pytest.mark.skipif(
    not _auth_smoke_ready(),
    reason="Set AUTH_PROVIDER=supabase + SUPABASE_URL + SUPABASE_ANON_KEY + DATABASE_URL for Auth smoke",
)


@requires_supabase_auth
class TestSupabaseAuthSmoke:
    """Auth JWT → /auth/me + tenant accounts list."""

    @pytest.fixture()
    def auth_client(self) -> TestClient:
        """Client with Auth provider settings from the process environment."""
        UsersService.ensure_password_manager()
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        return TestClient(create_app())

    def test_register_login_me_and_accounts(self, auth_client: TestClient) -> None:
        """Pass-through register/login then protected me + accounts."""
        suffix = uuid.uuid4().hex[:8]
        username = f"smk_{suffix}"
        email = f"smk_{suffix}@example.com"
        reg = auth_client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": email, "password": _VALID_PASSWORD},
        )
        assert reg.status_code == 201, reg.text

        login = auth_client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": _VALID_PASSWORD},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = auth_client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["email"] == email

        accounts = auth_client.get("/api/v1/accounts", headers=headers)
        assert accounts.status_code == 200, accounts.text
