"""Module for extracting package metadata from pyproject.toml.

This module provides functionality to extract and expose metadata from the package's
pyproject.toml file, including version number and authors information. It serves as
a central place for accessing package metadata throughout the application.

When installed from a wheel (PyPI), version comes from ``importlib.metadata``.
Source checkouts still read ``modules/model/pyproject.toml`` via toml.
"""

from __future__ import annotations

import logging
import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

import toml

logger = logging.getLogger(__name__)

_DISTRIBUTION_NAME = "papita-transactions-model"


def get_poetry_configs(module_path: str | os.PathLike | None = None) -> dict:
    """Extract project/Poetry configuration from the package's pyproject.toml file.

    Locates ``pyproject.toml`` relative to this module (source checkout) and returns
    the ``[project]`` table (falling back to ``[tool.poetry]`` for older layouts).

    Args:
        module_path: Optional path used to anchor the search (defaults to this file).

    Returns:
        dict: Project configuration from pyproject.toml, or ``{}`` if missing/unreadable.
    """
    module_path = module_path or __file__
    pyproject_path = Path(os.path.dirname(os.path.abspath(module_path))).parent.joinpath("pyproject.toml")

    if not pyproject_path.exists():
        pyproject_path_parent = pyproject_path.parent.parent.joinpath("pyproject.toml")
        if not pyproject_path_parent.exists():
            logger.debug(
                "pyproject.toml not found at %s or %s",
                pyproject_path,
                pyproject_path_parent,
            )
            return {}
        pyproject_path = pyproject_path_parent

    try:
        pyproject_data = toml.load(pyproject_path)
    except toml.TomlDecodeError:
        logger.exception("Error while decoding pyproject.toml due to:")
        return {}

    poetry_configs = pyproject_data.get("tool", {}).get("poetry", {})
    if not poetry_configs or not poetry_configs.get("version"):
        poetry_configs = pyproject_data.get("project", {})
    return poetry_configs


def _resolve_version(configs: dict) -> str:
    """Return distribution version from metadata, then pyproject, then default."""
    try:
        return package_version(_DISTRIBUTION_NAME).replace("v", "")
    except PackageNotFoundError:
        pass
    return str(configs.get("version", "0.0.1")).replace("v", "")


__configs__ = get_poetry_configs(module_path=__file__)

__authors__ = __configs__.get("authors", {})

__version__ = _resolve_version(__configs__)
