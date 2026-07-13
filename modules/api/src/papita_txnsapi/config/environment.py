"""Resolve monorepo environment directories via ``PAPITA_ENV``.

Active environment selection:

* Env var ``PAPITA_ENV`` — one of ``local``, ``staging``, ``production`` (default ``local``).
* Files live under ``environments/<name>/.env`` (templates: ``.env.example``).

Deploy scripts mirror this with ``--env <name>``; see ``environments/README.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

KNOWN_ENVIRONMENTS: frozenset[str] = frozenset({"local", "staging", "production"})
DEFAULT_ENVIRONMENT = "local"
ENV_VAR_NAME = "PAPITA_ENV"


def repo_root() -> Path:
    """Return the monorepo root (directory that contains ``environments/``).

    Returns:
        Absolute path to the repository root.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "environments").is_dir() and (parent / "modules").is_dir():
            return parent
    return here.parents[4]


def normalize_environment_name(name: str | None) -> str:
    """Validate and normalize an environment name.

    Args:
        name: Raw name (e.g. from ``PAPITA_ENV`` or ``--env``). Empty/None → default.

    Returns:
        One of ``local``, ``staging``, ``production``.

    Raises:
        ValueError: When ``name`` is set but not a known environment.
    """
    if name is None or str(name).strip() == "":
        return DEFAULT_ENVIRONMENT
    normalized = str(name).strip().lower()
    if normalized not in KNOWN_ENVIRONMENTS:
        allowed = ", ".join(sorted(KNOWN_ENVIRONMENTS))
        raise ValueError(f"Unknown PAPITA_ENV={name!r}; expected one of: {allowed}")
    return normalized


def active_environment(*, override: str | None = None) -> str:
    """Return the active environment name.

    Args:
        override: Explicit name (wins over ``PAPITA_ENV``).

    Returns:
        Normalized environment name.
    """
    if override is not None and str(override).strip() != "":
        return normalize_environment_name(override)
    return normalize_environment_name(os.environ.get(ENV_VAR_NAME))


def env_dir(*, name: str | None = None) -> Path:
    """Return ``environments/<name>/`` for the active or requested environment.

    Args:
        name: Explicit environment folder name; defaults to :func:`active_environment`.

    Returns:
        Absolute path to the environment directory (may not exist yet).
    """
    resolved = active_environment(override=name)
    return repo_root() / "environments" / resolved


def env_file(*, name: str | None = None) -> Path:
    """Return ``environments/<name>/.env`` for the active or requested environment.

    Args:
        name: Explicit environment folder name; defaults to :func:`active_environment`.

    Returns:
        Absolute path to the ``.env`` file (may be missing).
    """
    return env_dir(name=name) / ".env"


def env_file_for_settings(*, name: str | None = None) -> Path | None:
    """Path for Pydantic Settings ``_env_file``, or ``None`` if the file is absent.

    Missing files keep CI/unit tests working with process env only.
    """
    path = env_file(name=name)
    return path if path.is_file() else None
