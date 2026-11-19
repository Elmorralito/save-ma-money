"""Email sources for ingestion."""

from papita_ingestor_email.sources.gmail import GmailSource, create_gmail_source
from papita_ingestor_email.sources.query import build_gmail_query

__all__ = ["GmailSource", "build_gmail_query", "create_gmail_source"]
