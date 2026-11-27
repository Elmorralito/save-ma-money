"""Security helpers for untrusted Gmail messages, headers, and error redaction."""

from __future__ import annotations

import re
from collections.abc import Mapping
from email.utils import parseaddr

# Strict allowlist of MIME headers retained on RawRecord.metadata.
# Excludes Received, Delivered-To, To, Cc, Bcc, X-*, and tracking headers.
SAFE_MIME_HEADERS: frozenset[str] = frozenset(
    {
        "from",
        "subject",
        "date",
        "message-id",
        "authentication-results",
        "arc-authentication-results",
    }
)

# C0/C1 control chars (except \t, \n, \r) + Unicode BiDi spoofing overrides.
_CONTROL_AND_BIDI_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_WHITESPACE_RE = re.compile(r"\s+")

# Potential 13-19 digit PAN/card numbers (with optional spaces or hyphens).
_PAN_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_SECRET_TOKEN_RE = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|ya29\.[A-Za-z0-9._-]{16,}|1//[A-Za-z0-9._-]{16,})",
    re.IGNORECASE,
)

_AUTH_DKIM_PASS_RE = re.compile(r"\bdkim\s*=\s*pass\b", re.IGNORECASE)
_AUTH_SPF_PASS_RE = re.compile(r"\bspf\s*=\s*pass\b", re.IGNORECASE)
_AUTH_DMARC_PASS_RE = re.compile(r"\bdmarc\s*=\s*pass\b", re.IGNORECASE)
_AUTH_EXPLICIT_FAIL_RE = re.compile(r"\b(?:dkim|spf|dmarc)\s*=\s*(?:fail|permerror)\b", re.IGNORECASE)


def sanitize_untrusted_text(text: str, *, max_len: int = 64_000) -> str:
    """Strip control/BiDi spoofing characters, collapse whitespace, and bound length."""
    if not text:
        return ""
    cleaned = _CONTROL_AND_BIDI_RE.sub("", text)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    return cleaned


def _mask_pan(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if 13 <= len(digits) <= 19:
        return f"****{digits[-4:]}"
    return match.group(0)


def redact_sensitive_text(text: str, *, max_len: int = 500) -> str:
    """Redact OAuth/Bearer tokens and full card numbers from descriptions, logs, and errors."""
    if not text:
        return ""
    cleaned = _CONTROL_AND_BIDI_RE.sub("", text)
    cleaned = _SECRET_TOKEN_RE.sub("[REDACTED_TOKEN]", cleaned)
    cleaned = _PAN_RE.sub(_mask_pan, cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    return cleaned


def extract_sender_addr(raw_from: str | None) -> str:
    """Extract only the RFC 5322 addr-spec from a ``From`` header.

    Prevents display-name spoofing such as
    ``"Nu <nu@nu.com.co>" <attacker@evil.com>`` from matching bank domain regexes.
    """
    if not raw_from:
        return ""
    cleaned = _CONTROL_AND_BIDI_RE.sub("", raw_from).strip()
    _, addr = parseaddr(cleaned)
    if addr and "@" in addr:
        return addr.strip().lower()
    # Fallback for bare domain/address tokens without angle brackets.
    if "@" in cleaned and " " not in cleaned:
        return cleaned.lower()
    return ""


def verify_email_authentication(headers: Mapping[str, str] | None) -> tuple[bool, str]:
    """Verify DKIM/SPF/DMARC signals in Gmail ``Authentication-Results`` headers.

    When authentication headers are absent (e.g., synthetic local fixtures), returns
    ``(True, "no_auth_header")``. When present, rejects messages that explicitly
    failed authentication without a passing DKIM or DMARC signature.

    Returns:
        ``(is_trusted, reason)`` tuple.
    """
    if not headers:
        return True, "no_auth_header"

    auth_values = [
        value
        for key, value in headers.items()
        if key.lower() in {"authentication-results", "arc-authentication-results"} and value
    ]
    if not auth_values:
        return True, "no_auth_header"

    combined = " ; ".join(auth_values)
    has_dkim_pass = bool(_AUTH_DKIM_PASS_RE.search(combined))
    has_spf_pass = bool(_AUTH_SPF_PASS_RE.search(combined))
    has_dmarc_pass = bool(_AUTH_DMARC_PASS_RE.search(combined))
    has_fail = bool(_AUTH_EXPLICIT_FAIL_RE.search(combined))

    if has_dmarc_pass or has_dkim_pass:
        return True, "dkim_or_dmarc_pass"
    if has_fail:
        return False, "auth_explicit_fail"
    if has_spf_pass:
        return True, "spf_pass"
    return False, "auth_no_pass_signal"


__all__ = [
    "SAFE_MIME_HEADERS",
    "extract_sender_addr",
    "redact_sensitive_text",
    "sanitize_untrusted_text",
    "verify_email_authentication",
]
