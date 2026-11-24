"""Gmail search query builder (PPT-080 / #174)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from papita_ingestor_core.types.records import FetchFilter


def _quote_term(term: str) -> str:
    """Quote Gmail search terms that contain whitespace or quotes."""
    if any(ch.isspace() for ch in term) or '"' in term:
        escaped = term.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return term


def _collect_terms(single: Any, multiple: Any) -> list[str]:
    """Combine legacy scalar and list filter values into deduplicated, non-empty terms."""
    raw: list[str] = []
    if isinstance(single, str):
        raw.append(single)
    elif isinstance(single, Iterable):
        raw.extend(str(item) for item in single)

    if isinstance(multiple, str):
        raw.extend(multiple.split(","))
    elif isinstance(multiple, Iterable):
        raw.extend(str(item) for item in multiple)

    seen: set[str] = set()
    terms: list[str] = []
    for item in raw:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            terms.append(cleaned)
    return terms


def _format_from_clause(senders: list[str]) -> str:
    """Format one or more Gmail ``from:`` sender/domain terms."""
    quoted = [_quote_term(sender) for sender in senders]
    if len(quoted) == 1:
        return f"from:{quoted[0]}"
    return f"from:({' OR '.join(quoted)})"


def _format_subject_clause(subjects: list[str]) -> str:
    """Format one or more Gmail ``subject:`` terms."""
    quoted = [_quote_term(subject) for subject in subjects]
    if len(quoted) == 1:
        return f"subject:({quoted[0]})"
    return f"subject:({' OR '.join(quoted)})"


def build_gmail_query(
    fetch_filter: FetchFilter | None,
    *,
    processed_label: str,
) -> str:
    """Build a Gmail ``messages.list`` ``q`` string.

    Always excludes the processed label so acknowledged mail is not re-fetched.
    Supports ``FetchFilter.since`` / ``until`` (epoch seconds), and ``extra`` keys:

    - ``source_label`` / ``label``: restrict fetch to a specific Gmail label.
    - ``sender`` / ``senders``: one or more sender addresses/domains.
    - ``subject`` / ``subjects``: one or more subject keywords/phrases.
    - ``q``: raw Gmail search query fragment.
    """
    parts: list[str] = [f"-label:{_quote_term(processed_label)}"]
    if fetch_filter is None:
        return " ".join(parts)

    if fetch_filter.since is not None:
        parts.append(f"after:{int(fetch_filter.since.timestamp())}")
    if fetch_filter.until is not None:
        parts.append(f"before:{int(fetch_filter.until.timestamp())}")

    extra = fetch_filter.extra
    source_label = extra.get("source_label") or extra.get("label")
    if isinstance(source_label, str) and source_label.strip():
        parts.append(f"label:{_quote_term(source_label.strip())}")

    senders = _collect_terms(extra.get("sender"), extra.get("senders"))
    if senders:
        parts.append(_format_from_clause(senders))

    subjects = _collect_terms(extra.get("subject"), extra.get("subjects"))
    if subjects:
        parts.append(_format_subject_clause(subjects))

    raw_q = extra.get("q")
    if raw_q is not None and str(raw_q).strip():
        cleaned_q = " ".join(str(raw_q).split())
        parts.append(f"({cleaned_q})" if " " in cleaned_q else cleaned_q)

    return " ".join(parts)


__all__ = ["build_gmail_query"]
