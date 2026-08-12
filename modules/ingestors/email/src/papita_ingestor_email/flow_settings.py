"""Email Prefect flow settings (``PAPITA_INGESTOR_*``) — PPT-082 / #176."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from papita_ingestor_core.settings.base import BaseIngestorSettings


class EmailFlowSettings(BaseIngestorSettings):
    """Runner + schedule knobs for the email ingestion Prefect flow.

    Shares ``PAPITA_INGESTOR_`` with ``BaseIngestorSettings`` (``fetch_limit``,
    ``dry_run``). Gmail credentials stay on ``GmailSettings`` / ``GMAIL_*``.
    """

    owner_id: UUID
    lookback_hours: int = Field(default=24, ge=1)
    schedule_interval_minutes: int = Field(default=60, ge=1)
    flow_retries: int = Field(default=2, ge=0)
    flow_retry_delay_seconds: float = Field(default=60, ge=0)


__all__ = ["EmailFlowSettings"]
