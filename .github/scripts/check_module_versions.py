#!/usr/bin/env python3
"""Validate Poetry module version fields are present and parseable."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULES_PATH = PROJECT_ROOT / "modules"
VERSION_PATTERN = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+(?:[a-z]\d+)?(?:[-+][0-9A-Za-z.-]+)?)$")


def load_version(pyproject_path: Path) -> str:
    """Load the project version from a pyproject.toml file."""
    with pyproject_path.open("rb") as file:
        data = tomllib.load(file)
    project = data.get("project", {})
    version = project.get("version")
    if not version:
        raise ValueError(f"Missing [project].version in {pyproject_path}")
    return str(version)


def validate_version(version: str) -> None:
    """Validate a Poetry-style version string."""
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid version format: {version}")


def main() -> int:
    """Validate versions for all module pyproject.toml files."""
    pyproject_files = sorted(MODULES_PATH.glob("*/pyproject.toml"))
    if not pyproject_files:
        print("No module pyproject.toml files found.", file=sys.stderr)
        return 1

    errors: list[str] = []
    for pyproject_path in pyproject_files:
        module_name = pyproject_path.parent.name
        try:
            version = load_version(pyproject_path)
            validate_version(version)
            print(f"OK  {module_name}: {version}")
        except ValueError as exc:
            errors.append(f"{module_name}: {exc}")

    if errors:
        print("Module version validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
