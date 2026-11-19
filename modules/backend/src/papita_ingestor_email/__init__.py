"""Gmail / email ingestion plugin (PPT-098 / #261)."""

from __future__ import annotations

from papita_ingestor_email.__meta__ import __version__
from papita_ingestor_email.parsers import BancolombiaParser, FallbackEmailParser, NequiParser, default_email_parsers
from papita_ingestor_email.settings import GmailSettings
from papita_ingestor_email.sources import GmailSource, create_gmail_source

__all__ = [
    "BancolombiaParser",
    "FallbackEmailParser",
    "GmailSettings",
    "GmailSource",
    "NequiParser",
    "create_gmail_source",
    "default_email_parsers",
    "__version__",
]
