"""COP amount and timestamp helpers for Colombian bank email parsers."""

from __future__ import annotations

import re
from datetime import datetime

# Matches US ($72,000.00 / $2000000.00) and Colombian ($400.000,00 / COP143.099,00) amounts.
_AMOUNT_RE = re.compile(r"(?:\$|COP)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)
_DMY_DATE_RE = re.compile(
    r"(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>\d{2,4})(?:\s*(?:a\s+las\s+)?(?P<h>\d{1,2}):(?P<min>\d{2})(?::(?P<s>\d{2}))?)?",
    re.IGNORECASE,
)
_YMD_DATE_RE = re.compile(
    r"(?P<y>\d{4})/(?P<m>\d{1,2})/(?P<d>\d{1,2})(?:\s*(?:a\s+las\s+)?(?P<h>\d{1,2}):(?P<min>\d{2})(?::(?P<s>\d{2}))?)?",
    re.IGNORECASE,
)
# Bancolombia payroll variant: "el 09:54 a las 13/11/2026"
_TIME_FIRST_DMY_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<min>\d{2})\s+a\s+las\s+(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>\d{2,4})",
    re.IGNORECASE,
)
_MASKED_ACCOUNT_RE = re.compile(r"\*+\s*(\d{4})")


def _normalize_cop_number(raw: str) -> float | None:
    cleaned = raw.strip().replace(" ", "")
    if not cleaned:
        return None
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts[-1]) == 3 and all(len(p) == 3 for p in parts[1:]):
            cleaned = "".join(parts)
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_cop_amount(text: str) -> float | None:
    """Parse the first ``$`` or ``COP`` amount (US or Colombian format) into a positive float."""
    for match in _AMOUNT_RE.finditer(text):
        amount = _normalize_cop_number(match.group(1))
        if amount is not None:
            return amount
    return None


def parse_spanish_datetime(text: str) -> datetime | None:
    """Parse ``DD/MM/YYYY``, ``YYYY/MM/DD``, or ``HH:MM a las DD/MM/YYYY`` from Spanish alerts."""
    for pattern in (_TIME_FIRST_DMY_RE, _YMD_DATE_RE, _DMY_DATE_RE):
        match = pattern.search(text)
        if match is None:
            continue
        day = int(match.group("d"))
        month = int(match.group("m"))
        year = int(match.group("y"))
        if year < 100:
            year += 2000
        hour = int(match.group("h") or 0)
        minute = int(match.group("min") or 0)
        second = int(match.groupdict().get("s") or 0)
        try:
            return datetime(year, month, day, hour, minute, second)
        except ValueError:
            continue
    return None


def extract_masked_account(text: str) -> str | None:
    """Return the last-4 digits from a masked product token like ``*7756`` or ``* 0801``."""
    match = _MASKED_ACCOUNT_RE.search(text)
    if match is None:
        return None
    return match.group(1)


__all__ = [
    "extract_masked_account",
    "parse_cop_amount",
    "parse_spanish_datetime",
]
