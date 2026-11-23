"""Plugin manifest and capability metadata for ingestion connectors."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.model.enums import IngestionSource

PluginKind = Literal["pull_source", "record_parser", "batch_importer", "rate_feed"]


class PluginManifest(BaseModel):
    """Non-secret metadata describing a registered connector, parser, or importer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plugin_id: str = Field(min_length=1, max_length=128)
    kind: PluginKind
    version: str = Field(default="1.0.0", min_length=1, max_length=32)
    ingestion_source: IngestionSource
    supported_source_ids: frozenset[str] | None = None
    supported_ingestion_sources: frozenset[IngestionSource] | None = None
    supported_media_types: tuple[str, ...] = ()
    capabilities: frozenset[str] = frozenset()
    description: str = ""


__all__ = ["PluginKind", "PluginManifest"]
