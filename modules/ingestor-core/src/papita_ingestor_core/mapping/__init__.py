"""Mapping helpers between core DTOs and the model bridge."""

from __future__ import annotations

from papita_ingestor_core.mapping.raw_payload import encode_raw_payload
from papita_ingestor_core.mapping.to_bridge import to_ingest_transaction_request

__all__ = ["encode_raw_payload", "to_ingest_transaction_request"]
