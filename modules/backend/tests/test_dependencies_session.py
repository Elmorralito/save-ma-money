"""Tests for papita_txnsapi.dependencies.session."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi import HTTPException, Response

from papita_txnsapi.core.security.auth import AuthSecurityManager
from papita_txnsmodel.helpers.hashing.argon2 import Argon2PasswordManager
from papita_txnsmodel.helpers.hashing.factory import PasswordManagerFactory
from papita_txnsapi.core.settings import APISettings, get_settings
from papita_txnsapi.dependencies.session import (
    REFRESH_TOKEN_HEADER,
    UserSession,
    _session_from_token,
    get_current_user_session_kept_alive,
    get_issue_session_token,
    get_verify_credentials,
)


@pytest.fixture(autouse=True)
def reset_password_manager_factory() -> None:
    PasswordManagerFactory().reset()
    yield
    PasswordManagerFactory().reset()


@pytest.fixture
def api_settings(monkeypatch: pytest.MonkeyPatch) -> APISettings:
    monkeypatch.setenv("JWT_SECRET_KEY", "ci-test-jwt-secret-key-min-32chars-x")
    get_settings.cache_clear()
    settings = APISettings()
    yield settings
    get_settings.cache_clear()


def test_session_from_token_valid(api_settings: APISettings) -> None:
    auth = AuthSecurityManager(api_settings)
    token = auth.generate_token("user-42")
    session = _session_from_token(token, auth, api_settings)
    assert session.user_id == "user-42"
    assert session.payload.get("sub") == "user-42"


def test_session_from_token_rejects_invalid_jwt(api_settings: APISettings) -> None:
    auth = AuthSecurityManager(api_settings)
    with pytest.raises(HTTPException) as exc_info:
        _session_from_token("not-a-valid-jwt", auth, api_settings)
    assert exc_info.value.status_code == 401


def test_verify_credentials_success(api_settings: APISettings) -> None:
    pm = Argon2PasswordManager()
    pm.setup_algorithm()
    hashed = pm.hash_password("SecretPass1!")
    user_id = str(uuid.uuid4())
    df = pd.DataFrame([{"id": user_id, "password": hashed, "active": True, "deleted_at": None}])

    with patch("papita_txnsapi.dependencies.session.UsersRepository") as mock_repo:
        mock_repo.return_value.get_records.return_value = df
        verify = get_verify_credentials(pm)
        assert verify("testuser", "SecretPass1!") == user_id


def test_verify_credentials_wrong_password(api_settings: APISettings) -> None:
    pm = Argon2PasswordManager()
    pm.setup_algorithm()
    hashed = pm.hash_password("SecretPass1!")
    df = pd.DataFrame([{"id": str(uuid.uuid4()), "password": hashed, "active": True, "deleted_at": None}])

    with patch("papita_txnsapi.dependencies.session.UsersRepository") as mock_repo:
        mock_repo.return_value.get_records.return_value = df
        verify = get_verify_credentials(pm)
        assert verify("testuser", "WrongPass1!") is None


def test_issue_session_token_roundtrip(api_settings: APISettings) -> None:
    pm = Argon2PasswordManager()
    pm.setup_algorithm()
    hashed = pm.hash_password("SecretPass1!")
    user_id = str(uuid.uuid4())
    df = pd.DataFrame([{"id": user_id, "password": hashed, "active": True, "deleted_at": None}])

    with patch("papita_txnsapi.dependencies.session.UsersRepository") as mock_repo:
        mock_repo.return_value.get_records.return_value = df
        auth = AuthSecurityManager(api_settings)
        verify = get_verify_credentials(pm)
        issue = get_issue_session_token(auth, verify)
        token = issue("someone", "SecretPass1!")
        assert token is not None
        session = _session_from_token(token, auth, api_settings)
        assert session.user_id == user_id


def test_kept_alive_sets_header_when_threshold_hit(api_settings: APISettings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_settings, "JWT_SLIDING_REFRESH_ENABLED", True)
    monkeypatch.setattr(api_settings, "JWT_REFRESH_THRESHOLD_SECONDS", 3600)
    auth = AuthSecurityManager(api_settings)
    token = auth.generate_token("sub-x")
    response = Response()
    session = get_current_user_session_kept_alive(
        response=response,
        token=token,
        auth=auth,
        settings=api_settings,
    )
    assert isinstance(session, UserSession)
    assert REFRESH_TOKEN_HEADER in response.headers


def test_renew_access_token(api_settings: APISettings) -> None:
    auth = AuthSecurityManager(api_settings)
    t1 = auth.generate_token("uid")
    t2 = auth.renew_access_token(t1)
    assert t2 is not None
    p2 = auth.decode_token(t2)
    assert p2 is not None
    assert p2.get("sub") == "uid"
