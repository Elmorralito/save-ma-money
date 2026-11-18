"""COP amount and timestamp helpers for Colombian bank email parsers."""

from __future__ import annotations

import re
from datetime import datetime

# Bancolombia-style: $20,000 or $3,000,000.00 (US thousands commas).
_AMOUNT_RE = re.compile(r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)")
_DATE_RE = re.compile(
    r"(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>\d{2,4})(?:\s*(?:a\s+las\s+)?(?P<h>\d{1,2}):(?P<min>\d{2}))?",
    re.IGNORECASE,
)
_MASKED_ACCOUNT_RE = re.compile(r"\*+\s*(\d{4})")


def parse_cop_amount(text: str) -> float | None:
    """Parse the first ``$`` amount with US-style thousands separators into a float.

    Args:
        text: Visible email body text.

    Returns:
        Positive amount, or ``None`` when no match.
    """
    match = _AMOUNT_RE.search(text)
    if match is None:
        return None
    raw = match.group(1).replace(",", "")
    try:
        amount = float(raw)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return amount


def parse_spanish_datetime(text: str) -> datetime | None:
    """Parse ``DD/MM/YYYY`` or ``DD/MM/YY`` with optional ``HH:MM`` from Spanish alerts."""
    match = _DATE_RE.search(text)
    if match is None:
        return None
    day = int(match.group("d"))
    month = int(match.group("m"))
    year = int(match.group("y"))
    if year < 100:
        year += 2000
    hour = int(match.group("h") or 0)
    minute = int(match.group("min") or 0)
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def extract_masked_account(text: str) -> str | None:
    """Return the last-4 digits from a masked product token like ``*7756``."""
    match = _MASKED_ACCOUNT_RE.search(text)
    if match is None:
        return None
    return match.group(1)


__all__ = [
    "extract_masked_account",
    "parse_cop_amount",
    "parse_spanish_datetime",
]
