#!/usr/bin/env python3
"""Stamp modules/model/pyproject.toml with a unique PEP 440 dev version for TestPyPI.

Format: ``{base_version}.dev{run_id}`` (no local ``+`` segment — PyPI rejects those).

Usage:
    python .github/scripts/stamp_model_dev_version.py --run-id 1234567890
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
DEV_SUFFIX_RE = re.compile(r"\.dev\d+$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def stamp_dev_version(*, run_id: str, pyproject: Path) -> str:
    """Rewrite project.version to ``{base}.dev{run_id}`` and return the new version."""
    if not run_id.isdigit():
        raise ValueError(f"run_id must be numeric (GitHub run id), got: {run_id!r}")

    text = pyproject.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"No project version field found in {pyproject}")

    base = DEV_SUFFIX_RE.sub("", match.group(1))
    new_version = f"{base}.dev{run_id}"
    new_text, count = VERSION_RE.subn(f'version = "{new_version}"', text, count=1)
    if count != 1:
        raise RuntimeError(f"Failed to rewrite version in {pyproject}")

    pyproject.write_text(new_text, encoding="utf-8")
    return new_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="GitHub Actions run id (numeric)")
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=None,
        help="Path to modules/model/pyproject.toml (default: repo-relative)",
    )
    args = parser.parse_args(argv)

    pyproject = args.pyproject or (_repo_root() / "modules" / "model" / "pyproject.toml")
    if not pyproject.is_file():
        print(f"error: pyproject not found: {pyproject}", file=sys.stderr)
        return 1

    try:
        new_version = stamp_dev_version(run_id=args.run_id, pyproject=pyproject)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(new_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
