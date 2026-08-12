"""Email / Gmail source plugins."""

from __future__ import annotations

from papita_ingestor_email.sources.gmail import GmailSource, create_gmail_source, ensure_registered
from papita_ingestor_email.sources.query import build_gmail_query

ensure_registered()

__all__ = [
    "GmailSource",
    "build_gmail_query",
    "create_gmail_source",
    "ensure_registered",
]
