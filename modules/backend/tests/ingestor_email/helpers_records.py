"""Shared RawRecord builders for email parser tests."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path

from papita_ingestor_core.types.records import RawRecord
from papita_txnsmodel.model.enums import IngestionSource

FIXTURES = Path(__file__).parent / "fixtures" / "emails"


def load_eml(name: str) -> bytes:
    """Read a committed MIME fixture."""
    return (FIXTURES / name).read_bytes()


def raw_from_eml(name: str, *, source_ref: str = "gmail-msg-1") -> RawRecord:
    """Build a Gmail-shaped ``RawRecord`` from a fixture ``.eml`` file."""
    content = load_eml(name)
    parsed = BytesParser(policy=policy.default).parsebytes(content)
    return RawRecord(
        source_id="gmail",
        source_ref=source_ref,
        content=content,
        metadata={
            "subject": parsed.get("Subject"),
            "sender": parsed.get("From"),
            "headers": {str(k): str(v) for k, v in parsed.items()},
        },
        ingestion_source=IngestionSource.EMAIL,
    )


__all__ = ["FIXTURES", "load_eml", "raw_from_eml"]
