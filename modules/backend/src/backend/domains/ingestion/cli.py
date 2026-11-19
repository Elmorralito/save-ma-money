"""CLI entrypoint for email ingestion batch runs (``python -m backend.domains.ingestion.cli --once``)."""

from __future__ import annotations

from papita_ingestor_email.flows.email_flow import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

__all__ = ["main"]
