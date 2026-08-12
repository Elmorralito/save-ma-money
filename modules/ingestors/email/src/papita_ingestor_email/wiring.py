"""Shared dependency bundle for email runner + Prefect flow (PPT-082 / #176)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from papita_ingestor_core.runner.ingestion_runner import OwnerProvider
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.settings import GmailSettings


@dataclass(frozen=True, slots=True)
class EmailFlowDeps:
    """Single wiring object for ``build_email_runner`` / ``build_email_ingestion_flow``.

    Avoids duplicating the same keyword surface on both factories.
    """

    flow_settings: EmailFlowSettings | None = None
    gmail_settings: GmailSettings | None = None
    source: BaseIngestorSource | None = None
    bridge: Any | None = None
    owner: OwnerProvider | None = None
    establish_db: bool | None = None
    verify_owner: bool | None = None


__all__ = ["EmailFlowDeps"]
