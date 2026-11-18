"""Prefect email ingestion flows (optional Prefect install)."""

from __future__ import annotations

from papita_ingestor_email.flows.email_flow import (
    build_email_ingestion_flow,
    build_email_runner,
    default_fetch_filter,
    serve_email_ingestion,
)
from papita_ingestor_email.wiring import EmailFlowDeps

__all__ = [
    "EmailFlowDeps",
    "build_email_ingestion_flow",
    "build_email_runner",
    "default_fetch_filter",
    "serve_email_ingestion",
]
