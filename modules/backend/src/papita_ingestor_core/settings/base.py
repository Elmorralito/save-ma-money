"""Common ingestor settings (no FK defaults — PPT-079 / #173)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseIngestorSettings(BaseSettings):
    """Shared knobs for ingestion runs; plugins may subclass.

    ``IngestionRunner`` honors:

    - ``fetch_limit``: applied when ``FetchFilter.limit`` is unset (and as a
      hard cap while streaming).
    - ``dry_run``: parse/validate only — no bridge persist, no DLQ, no ack.
    """

    model_config = SettingsConfigDict(extra="ignore", env_prefix="PAPITA_INGESTOR_")

    fetch_limit: int | None = Field(default=None, ge=1)
    dry_run: bool = False


__all__ = ["BaseIngestorSettings"]
