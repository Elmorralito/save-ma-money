"""Email ingestion flow settings (``PAPITA_INGESTOR_*``) — PPT-082 / #176."""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, field_validator
from pydantic_settings import NoDecode

from papita_ingestor_core.settings.base import BaseIngestorSettings


def _parse_str_list(value: Any) -> list[str]:
    """Parse comma-separated strings, JSON arrays, or Python iterables into clean terms."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                return [str(item).strip() for item in decoded if str(item).strip()]
        return [part.strip() for part in stripped.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    raise TypeError(f"Expected string or sequence of strings, got {type(value).__name__}")


def _normalize_optional_str(value: Any) -> str | None:
    """Trim optional string settings and treat blank strings as ``None``."""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


class EmailFlowSettings(BaseIngestorSettings):
    """Runner, schedule, and Gmail channel filter knobs for email ingestion.

    Shares ``PAPITA_INGESTOR_`` with ``BaseIngestorSettings`` (``fetch_limit``,
    ``dry_run``). Gmail credentials stay on ``GmailSettings`` / ``GMAIL_*``.
    """

    owner_id: UUID
    lookback_hours: int = Field(default=24, ge=1, le=720)
    schedule_interval_minutes: int = Field(default=60, ge=1)
    flow_retries: int = Field(default=2, ge=0)
    flow_retry_delay_seconds: float = Field(default=60, ge=0)
    email_senders: Annotated[list[str], NoDecode] = Field(default_factory=list)
    email_subjects: Annotated[list[str], NoDecode] = Field(default_factory=list)
    email_source_label: str | None = None
    email_query: str | None = None

    @field_validator("email_senders", "email_subjects", mode="before")
    @classmethod
    def _coerce_filter_lists(cls, value: Any) -> list[str]:
        return _parse_str_list(value)

    @field_validator("email_source_label", "email_query", mode="before")
    @classmethod
    def _coerce_optional_filters(cls, value: Any) -> str | None:
        return _normalize_optional_str(value)


__all__ = ["EmailFlowSettings"]
