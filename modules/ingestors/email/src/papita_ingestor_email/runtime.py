"""Host/Compose runtime helpers for email ingestion (PPT-082 / #176).

Keeps the plugin free of ``papita_txnsapi`` imports while still honoring
``PAPITA_ENV`` / ``environments/<env>/.env`` and establishing the model DB
connector before bridge persist/DLQ.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

_KNOWN_ENVS = frozenset({"local", "staging", "production"})


def repo_root() -> Path:
    """Locate the monorepo root (has ``environments/`` and ``modules/``)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "environments").is_dir() and (parent / "modules").is_dir():
            return parent
    return here.parents[4]


def active_environment_name() -> str:
    """Return ``PAPITA_ENV`` normalized (default ``local``)."""
    raw = (os.environ.get("PAPITA_ENV") or "local").strip().lower()
    if raw not in _KNOWN_ENVS:
        raise ValueError(f"Unknown PAPITA_ENV={raw!r}; expected one of: {', '.join(sorted(_KNOWN_ENVS))}")
    return raw


def env_file_path() -> Path:
    """Return ``environments/<PAPITA_ENV>/.env`` path (may not exist)."""
    return repo_root() / "environments" / active_environment_name() / ".env"


def load_environment_file(*, override: bool = False) -> Path | None:
    """Load ``environments/<PAPITA_ENV>/.env`` into ``os.environ`` when present.

    Compose already injects vars; host ``make ingestor-flow`` does not. Uses
    python-dotenv when available, otherwise a minimal KEY=VALUE parser.

    Args:
        override: When True, file values replace existing env vars.

    Returns:
        Path loaded, or ``None`` if the file is missing.
    """
    path = env_file_path()
    if not path.is_file():
        logger.debug("No env file at %s (using process environment only)", path)
        return None

    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_file_simple(path, override=override)
    else:
        load_dotenv(path, override=override)

    logger.info("Loaded ingestion env from %s (PAPITA_ENV=%s)", path, active_environment_name())
    return path


def _load_env_file_simple(path: Path, *, override: bool) -> None:
    """Minimal ``.env`` loader when python-dotenv is not installed."""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip("'").strip('"')
        if override or key not in os.environ:
            os.environ[key] = value


def establish_database_from_env(*, require: bool = True) -> type[SQLDatabaseConnector] | None:
    """Call ``SQLDatabaseConnector.establish`` from ``DATABASE_URL``.

    The API does this in Settings; the ingestor worker must do it explicitly
    or bridge persist/DLQ raises ``connection hasn't been established``.

    Args:
        require: When True, missing ``DATABASE_URL`` raises ``ValueError``.

    Returns:
        The connector class, or ``None`` when not required and URL unset.
    """
    if SQLDatabaseConnector.engine is not None:
        return SQLDatabaseConnector

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        if require:
            raise ValueError(
                "DATABASE_URL is required for ingestion persist/DLQ. "
                "Set it in environments/<PAPITA_ENV>/.env or the process environment."
            )
        return None

    SQLDatabaseConnector.establish(connection=url)
    logger.info("SQLDatabaseConnector established for ingestion worker")
    return SQLDatabaseConnector


def require_gmail_auth_env() -> None:
    """Fail fast when neither Gmail token-file nor refresh-token triplet is set.

    Mirrors ``GmailSettings`` validation without constructing credentials yet
    (so Compose crash-loops become a clear startup error).
    """
    token_file = (os.environ.get("GMAIL_TOKEN_FILE") or "").strip()
    client_id = (os.environ.get("GMAIL_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("GMAIL_CLIENT_SECRET") or "").strip()
    refresh_token = (os.environ.get("GMAIL_REFRESH_TOKEN") or "").strip()
    if token_file or (client_id and client_secret and refresh_token):
        return
    raise ValueError(
        "Gmail auth requires GMAIL_TOKEN_FILE or "
        "GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET + GMAIL_REFRESH_TOKEN "
        "(set in environments/<PAPITA_ENV>/.env or Compose env)"
    )


def require_owner_in_database(owner_id: UUID) -> UsersDTO:
    """Resolve ``owner_id`` to an active ``users`` row (FK for persist/DLQ).

    Args:
        owner_id: ``PAPITA_INGESTOR_OWNER_ID``.

    Returns:
        The persisted ``UsersDTO``.

    Raises:
        ValueError: When the user is missing or inactive.
    """
    establish_database_from_env(require=True)
    found = UsersService().get_owner(owner_id)
    if found is None or found.id is None:
        raise ValueError(
            f"PAPITA_INGESTOR_OWNER_ID={owner_id} was not found as an active users.id. "
            "Create/link the user first (API register / seed), then retry."
        )
    return found


def warn_h1_incomplete_fk_mode(*, dry_run: bool) -> None:
    """Log the H1=B limitation so live operators do not expect ledger upserts."""
    if dry_run:
        logger.info("Ingestion dry_run=true — parse/validate only; no persist/DLQ/ack")
        return
    logger.warning(
        "H1=B: bank parsers leave account/category FKs unset. "
        "Live runs will DLQ-then-ack parsed mail without ledger upserts until an "
        "FK enricher lands. Prefer PAPITA_INGESTOR_DRY_RUN=true for smoke tests."
    )


def run_cli_preflight(*, owner_id: UUID, dry_run: bool, require_gmail: bool = True) -> UsersDTO | None:
    """Host/Compose startup checks before ``--once`` or serve.

    Returns:
        DB-backed owner when not ``dry_run``; otherwise ``None`` (caller uses env id).
    """
    warn_h1_incomplete_fk_mode(dry_run=dry_run)
    if require_gmail:
        require_gmail_auth_env()
    if dry_run:
        return None
    return require_owner_in_database(owner_id)


__all__ = [
    "active_environment_name",
    "env_file_path",
    "establish_database_from_env",
    "load_environment_file",
    "repo_root",
    "require_gmail_auth_env",
    "require_owner_in_database",
    "run_cli_preflight",
    "warn_h1_incomplete_fk_mode",
]
