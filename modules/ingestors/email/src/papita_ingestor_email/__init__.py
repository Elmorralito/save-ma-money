"""papita-ingestor-email — Gmail / email source plugin.

Depends on ``papita_ingestor_core`` only. Do not import this package from
``papita_txnsapi`` or ``@papita/web``.
"""

from __future__ import annotations

from papita_ingestor_email.__meta__ import __version__
from papita_ingestor_email.parsers import BancolombiaParser, FallbackEmailParser, NequiParser, ensure_parsers_registered
from papita_ingestor_email.settings import GmailSettings
from papita_ingestor_email.sources import GmailSource, create_gmail_source, ensure_registered

ensure_parsers_registered()

__all__ = [
    "BancolombiaParser",
    "FallbackEmailParser",
    "GmailSettings",
    "GmailSource",
    "NequiParser",
    "create_gmail_source",
    "ensure_parsers_registered",
    "ensure_registered",
    "__version__",
]
