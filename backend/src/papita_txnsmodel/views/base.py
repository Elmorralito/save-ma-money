"""Utilities for loading SQL view definitions from package resources."""

import pkgutil
import re


def read_data_from_package_file(package: str, filename: str, encoding: str = "utf-8") -> str:
    """Load and normalize SQL from a file bundled in a Python package.

    Whitespace is collapsed to single spaces so ``alembic check`` comparisons
    stay stable across formatting differences (SpectrumAI glue pattern).

    Args:
        package: Dotted package name containing the SQL file.
        filename: SQL filename relative to the package directory.
        encoding: Text encoding for the file contents.

    Returns:
        Normalized SQL string suitable for ``PGMaterializedView.definition``.

    Raises:
        ValueError: If the package resource cannot be read.
    """
    raw_data = pkgutil.get_data(package, filename)
    if not raw_data:
        raise ValueError(f"The data file {filename} from package '{package}' could not be read.")

    return re.sub(r"\s+", " ", raw_data.decode(encoding)).strip()
