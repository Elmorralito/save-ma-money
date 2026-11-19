"""Opaque encoding of RawRecord content for dead-letter storage."""

from __future__ import annotations

import base64

from papita_ingestor_core.types.records import RawRecord


def encode_raw_payload(record: RawRecord) -> str:
    """Encode ``record.content`` to a string without inspecting structure.

    ``str`` content is returned as-is. ``bytes`` are base64-encoded with a
    ``b64:`` prefix so round-trips remain unambiguous.
    """
    content = record.content
    if isinstance(content, str):
        return content
    if isinstance(content, bytes):
        return "b64:" + base64.b64encode(content).decode("ascii")
    raise TypeError(f"Unsupported RawRecord.content type: {type(content)!r}")


__all__ = ["encode_raw_payload"]
