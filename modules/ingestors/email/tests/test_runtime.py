"""Runtime env + DB establish helpers (PPT-082 / #176)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from papita_ingestor_email import runtime
from papita_ingestor_email.owner import users_dto_for_owner_id
from papita_ingestor_email.runtime import (
    establish_database_from_env,
    load_environment_file,
    require_gmail_auth_env,
    require_owner_in_database,
    run_cli_preflight,
)


def test_load_environment_file_missing_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPITA_ENV", "local")
    with patch.object(runtime, "repo_root", return_value=tmp_path):
        (tmp_path / "environments" / "local").mkdir(parents=True)
        assert load_environment_file() is None


def test_load_environment_file_sets_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPITA_ENV", "local")
    monkeypatch.delenv("PAPITA_INGESTOR_OWNER_ID", raising=False)
    env_dir = tmp_path / "environments" / "local"
    env_dir.mkdir(parents=True)
    (env_dir / ".env").write_text("PAPITA_INGESTOR_OWNER_ID=00000000-0000-4000-8000-000000000099\n", encoding="utf-8")
    with patch.object(runtime, "repo_root", return_value=tmp_path):
        loaded = load_environment_file(override=False)
    assert loaded is not None
    assert os.environ["PAPITA_INGESTOR_OWNER_ID"] == "00000000-0000-4000-8000-000000000099"


def test_establish_database_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with (
        patch.object(runtime.SQLDatabaseConnector, "engine", None),
        pytest.raises(ValueError, match="DATABASE_URL"),
    ):
        establish_database_from_env(require=True)


def test_establish_database_from_env_calls_establish(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://admin:admin@localhost:5435/papita")
    with (
        patch.object(runtime.SQLDatabaseConnector, "engine", None),
        patch.object(runtime.SQLDatabaseConnector, "establish") as establish,
    ):
        establish_database_from_env(require=True)
        establish.assert_called_once_with(connection="postgresql+psycopg2://admin:admin@localhost:5435/papita")


def test_require_gmail_auth_env_fails_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("GMAIL_TOKEN_FILE", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Gmail auth requires"):
        require_gmail_auth_env()


def test_require_gmail_auth_env_accepts_triplet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GMAIL_CLIENT_ID", "id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh")
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)
    require_gmail_auth_env()


def test_require_owner_in_database_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    owner_id = uuid.uuid4()
    with (
        patch.object(runtime, "establish_database_from_env"),
        patch.object(runtime.UsersService, "get_owner", return_value=None),
        pytest.raises(ValueError, match="not found"),
    ):
        require_owner_in_database(owner_id)


def test_run_cli_preflight_dry_run_skips_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GMAIL_CLIENT_ID", "id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh")
    assert run_cli_preflight(owner_id=uuid.uuid4(), dry_run=True) is None


def test_run_cli_preflight_live_returns_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GMAIL_CLIENT_ID", "id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh")
    owner_id = uuid.uuid4()
    db_owner = users_dto_for_owner_id(owner_id)
    with patch.object(runtime, "require_owner_in_database", return_value=db_owner) as require_owner:
        found = run_cli_preflight(owner_id=owner_id, dry_run=False)
    assert found is db_owner
    require_owner.assert_called_once_with(owner_id)
