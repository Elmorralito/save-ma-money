#!/usr/bin/env python3
"""Export FastAPI OpenAPI JSON for the web typegen artifact (PPT-065 / #130).

Primary path (B0-safe): build the app in-process and call ``app.openapi()``.
Does **not** require Compose, a live server, or ``DOCS_ENABLED`` (HTTP docs may
still be gated; schema generation is independent).

Optional ``--from-url`` fetches a running server's ``/api/openapi.json`` when
operators want live parity (fails clearly on connection errors or docs-off 404).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def resolve_repo_root() -> Path:
    """Walk upward from this file to the monorepo root."""
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "modules").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {Path(__file__).resolve()}")


REPO_ROOT = resolve_repo_root()
DEFAULT_OUT = REPO_ROOT / "modules" / "web" / "openapi" / "openapi.json"


def _apply_offline_env() -> None:
    """Set deterministic, DB-free env before importing the API package."""
    os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-only-secret-min-32-chars")
    os.environ["AUTH_PROVIDER"] = "local"
    os.environ.setdefault("AUTH_RATE_LIMIT_ENABLED", "false")
    os.environ.setdefault("API_RATE_LIMIT_ENABLED", "false")
    os.environ.setdefault("HEALTH_RATE_LIMIT_ENABLED", "false")
    os.environ.setdefault("REDIS_ENABLED", "false")
    os.environ.setdefault("REDIS_RATE_LIMIT_ENABLED", "false")
    os.environ.setdefault("DOCS_ENABLED", "true")
    os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')
    os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1","testserver"]')
    # Prefer empty URL so Settings does not require a live Postgres for schema dump.
    if "DATABASE_URL" not in os.environ and "TEST_DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = ""


# Hosts allowed for optional ``--from-url`` live fetch (local operator tool only).
_LIVE_FETCH_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Stable placeholder so package version bumps do not force artifact churn.
_NORMALIZED_INFO_VERSION = "0.0.0-contract"


def _canonical_json(schema: dict) -> str:
    """Return stable, diff-friendly OpenAPI JSON text."""
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _normalize_schema(schema: dict) -> dict:
    """Drop non-contract noise that would cause false-positive drift.

    Normalizes ``info.version`` (API package semver) so version-only releases do
    not require regenerating the web OpenAPI artifact.
    """
    normalized = dict(schema)
    info = dict(normalized.get("info") or {})
    info["version"] = _NORMALIZED_INFO_VERSION
    normalized["info"] = info
    return normalized


def _export_offline() -> dict:
    """Build the FastAPI app and return its OpenAPI schema dict."""
    _apply_offline_env()
    # Imports must happen after env is set (module-level ``app = create_app()``).
    from papita_txnsapi.config.settings import get_settings
    from papita_txnsapi.main import create_app

    get_settings.cache_clear()
    return _normalize_schema(create_app().openapi())


def _export_from_url(url: str, *, timeout: float) -> dict:
    """Fetch OpenAPI JSON from a running API (docs must be enabled)."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit(f"--from-url must be http(s); got scheme={parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host not in _LIVE_FETCH_ALLOWED_HOSTS:
        raise SystemExit(
            f"--from-url host {host!r} is not allowed "
            f"(allowed: {', '.join(sorted(_LIVE_FETCH_ALLOWED_HOSTS))}). "
            "Prefer offline sync (omit --from-url)."
        )

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 — localhost-only allowlist above
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(
                f"OpenAPI URL returned 404 ({url}). Enable docs on the running API "
                "(DEBUG=true or DOCS_ENABLED=true), or omit --from-url to use the "
                "offline exporter (recommended)."
            ) from exc
        raise SystemExit(f"Failed to fetch OpenAPI from {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach OpenAPI at {url}: {exc.reason}. "
            "Start the API (`make api-up`) with docs enabled, or omit --from-url "
            "for the offline exporter (recommended)."
        ) from exc

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Response from {url} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or "openapi" not in payload:
        raise SystemExit(f"Response from {url} is not an OpenAPI document.")
    return _normalize_schema(payload)


def _write_or_check(*, out_path: Path, content: str, check: bool) -> int:
    """Write artifact, or exit non-zero when ``check`` and content drifts."""
    if check:
        if not out_path.is_file():
            print(f"ERROR: missing OpenAPI artifact: {out_path}", file=sys.stderr)
            print("Run: make sync-openapi && make generate-types", file=sys.stderr)
            return 1
        existing = out_path.read_text(encoding="utf-8")
        if existing != content:
            print(
                f"ERROR: OpenAPI artifact drift: {out_path} is out of date vs API schema.",
                file=sys.stderr,
            )
            print("Fix: make sync-openapi && make generate-types", file=sys.stderr)
            return 1
        print(f"OK: OpenAPI artifact in sync ({out_path})")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for OpenAPI export / drift check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the committed artifact differs from a fresh export (no write).",
    )
    parser.add_argument(
        "--from-url",
        metavar="URL",
        help="Optional live fetch (e.g. http://localhost:8000/api/openapi.json). "
        "Default is offline app.openapi() — preferred for B0/CI.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout seconds when using --from-url (default: 10).",
    )
    args = parser.parse_args(argv)

    schema = _export_from_url(args.from_url, timeout=args.timeout) if args.from_url else _export_offline()
    content = _canonical_json(schema)
    return _write_or_check(out_path=args.out.resolve(), content=content, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
