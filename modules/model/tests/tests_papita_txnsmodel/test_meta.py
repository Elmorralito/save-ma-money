"""Tests for papita_txnsmodel package metadata helpers (PPT-024)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import toml

from papita_txnsmodel import __meta__


def test_get_poetry_configs_reads_project_table_from_checkout() -> None:
    """Source checkout resolves modules/model/pyproject.toml via parent walk."""
    configs = __meta__.get_poetry_configs(module_path=__meta__.__file__)
    assert configs.get("name") == "papita-transactions-model"
    assert "version" in configs
    assert str(configs["version"]).replace("v", "") == __meta__.__version__


def test_get_poetry_configs_returns_empty_when_missing(tmp_path: Path) -> None:
    """Missing pyproject.toml yields an empty dict (no raise)."""
    orphan = tmp_path / "pkg" / "nested" / "module.py"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("# stub\n", encoding="utf-8")
    assert __meta__.get_poetry_configs(module_path=orphan) == {}


def test_get_poetry_configs_returns_empty_on_toml_decode_error(tmp_path: Path) -> None:
    """Invalid TOML is logged and returns {}."""
    pkg = tmp_path / "broken"
    nested = pkg / "nested"
    nested.mkdir(parents=True)
    module = nested / "module.py"
    module.write_text("# stub\n", encoding="utf-8")
    # parent of nested is pkg; code looks at nested/pyproject then pkg/pyproject
    (pkg / "pyproject.toml").write_text("[[[[not-valid", encoding="utf-8")
    with patch.object(toml, "load", side_effect=toml.TomlDecodeError("bad", "", 0)):
        assert __meta__.get_poetry_configs(module_path=module) == {}


def test_resolve_version_prefers_distribution_metadata() -> None:
    """Installed wheel path uses importlib.metadata over pyproject configs."""
    with patch.object(__meta__, "package_version", return_value="v9.8.7"):
        assert __meta__._resolve_version({"version": "0.0.1"}) == "9.8.7"


def test_resolve_version_falls_back_to_configs_when_not_installed() -> None:
    """PackageNotFoundError falls back to pyproject version (strip leading v)."""
    with patch.object(__meta__, "package_version", side_effect=PackageNotFoundError("x")):
        assert __meta__._resolve_version({"version": "v1.2.3"}) == "1.2.3"


def test_resolve_version_default_when_configs_empty() -> None:
    """Missing version key defaults to 0.0.1."""
    with patch.object(__meta__, "package_version", side_effect=PackageNotFoundError("x")):
        assert __meta__._resolve_version({}) == "0.0.1"
