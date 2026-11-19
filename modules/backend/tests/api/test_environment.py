"""Tests for PAPITA_ENV environment path resolution."""

from __future__ import annotations

import pytest

from papita_txnsapi.config.environment import (
    DEFAULT_ENVIRONMENT,
    active_environment,
    env_dir,
    env_file,
    normalize_environment_name,
    repo_root,
)


class TestNormalizeEnvironmentName:
    def test_default_for_empty(self) -> None:
        assert normalize_environment_name(None) == DEFAULT_ENVIRONMENT
        assert normalize_environment_name("") == DEFAULT_ENVIRONMENT

    def test_accepts_known_names(self) -> None:
        assert normalize_environment_name("local") == "local"
        assert normalize_environment_name("STAGING") == "staging"
        assert normalize_environment_name("Production") == "production"

    def test_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown PAPITA_ENV"):
            normalize_environment_name("qa")


class TestPaths:
    def test_repo_root_contains_environments(self) -> None:
        root = repo_root()
        assert (root / "environments").is_dir()
        assert (root / "modules").is_dir()

    def test_env_file_layout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PAPITA_ENV", raising=False)
        assert env_file().name == ".env"
        assert env_file().parent.name == "local"
        assert env_dir(name="staging").name == "staging"
        assert env_file(name="production").as_posix().endswith("environments/production/.env")

    def test_active_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPITA_ENV", "staging")
        assert active_environment() == "staging"
        assert active_environment(override="production") == "production"
