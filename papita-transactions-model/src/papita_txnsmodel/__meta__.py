"""Module for extracting package metadata from pyproject.toml.

This module provides functionality to extract and expose metadata from the package's
pyproject.toml file, including version number and authors information. It serves as
a central place for accessing package metadata throughout the application.

The module defines the following variables:
- __configs__: Dictionary containing the Poetry configuration section from pyproject.toml
- __authors__: List of package authors extracted from the Poetry configuration
- __version__: Package version string, with any 'v' prefix removed
"""

import logging
import os
from pathlib import Path

import toml

logger = logging.getLogger(__name__)


def get_poetry_configs() -> dict:
    """Extract Poetry configuration from the package's pyproject.toml file.

    This function locates the pyproject.toml file by navigating from the current
    module's directory up to the parent directory, then attempts to read and parse
    the file to extract the Poetry configuration section.

    Returns:
        dict: A dictionary containing the Poetry configuration from pyproject.toml.
            Returns an empty dictionary if the file is not found or cannot be parsed.

    Raises:
        toml.TomlDecodeError: When the pyproject.toml file exists but contains invalid TOML.
            This exception is caught and logged, and an empty dictionary is returned.
    """
    pyproject_path = Path(os.path.dirname(os.path.abspath(__file__))).parent.joinpath("pyproject.toml")

    if not pyproject_path.exists():
        logger.debug("Error: pyproject.toml not found at %s", pyproject_path)
        return {}

    try:
        pyproject_data = toml.load(pyproject_path)
        return pyproject_data.get("tool", {}).get("poetry", {})
    except toml.TomlDecodeError:
        logger.exception("Error while decoding pyproject.toml due to:")
        return {}


__configs__ = get_poetry_configs()

__authors__ = __configs__.get("authors", {})

__version__ = __configs__.get("version", "0.0.1").replace("v", "")
