"""Gmail search query builder (PPT-080 / #174)."""

from __future__ import annotations

from papita_ingestor_core.types.records import FetchFilter


def _quote_label(label: str) -> str:
    """Quote label names that contain spaces for Gmail ``q`` syntax."""
    if " " in label or '"' in label:
        escaped = label.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return label


def build_gmail_query(
    fetch_filter: FetchFilter | None,
    *,
    processed_label: str,
) -> str:
    """Build a Gmail ``messages.list`` ``q`` string.

    Always excludes the processed label so acknowledged mail is not re-fetched.
    Supports ``FetchFilter.since`` / ``until`` (epoch seconds), and ``extra`` keys
    ``sender``, ``subject``, and ``q`` (raw fragment).
    """
    parts: list[str] = [f"-label:{_quote_label(processed_label)}"]
    if fetch_filter is None:
        return " ".join(parts)

    if fetch_filter.since is not None:
        parts.append(f"after:{int(fetch_filter.since.timestamp())}")
    if fetch_filter.until is not None:
        parts.append(f"before:{int(fetch_filter.until.timestamp())}")

    extra = fetch_filter.extra
    sender = extra.get("sender")
    if sender:
        parts.append(f"from:{sender}")
    subject = extra.get("subject")
    if subject:
        parts.append(f"subject:({subject})")
    raw_q = extra.get("q")
    if raw_q:
        parts.append(str(raw_q))

    return " ".join(parts)


__all__ = ["build_gmail_query"]
