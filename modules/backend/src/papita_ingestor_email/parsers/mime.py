"""MIME / HTML helpers for email bank parsers (PPT-081 / #175)."""

from __future__ import annotations

import re
from email import policy
from email.message import Message
from email.parser import BytesParser, Parser
from html.parser import HTMLParser

from papita_ingestor_email.parsers.security import extract_sender_addr, sanitize_untrusted_text

_WHITESPACE_RE = re.compile(r"\s+")
_SKIP_HTML_TAGS = frozenset({"script", "style", "head", "noscript", "template", "svg"})
_MAX_MIME_PARTS = 50
_MAX_PART_BYTES = 512_000
_MAX_EXTRACTED_TEXT_CHARS = 64_000


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text from HTML, ignoring script/style/hidden container bodies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._char_count = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _SKIP_HTML_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP_HTML_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data and self._char_count < _MAX_EXTRACTED_TEXT_CHARS:
            remaining = _MAX_EXTRACTED_TEXT_CHARS - self._char_count
            piece = data[:remaining]
            self._chunks.append(piece)
            self._char_count += len(piece)

    def text(self) -> str:
        return sanitize_untrusted_text("".join(self._chunks), max_len=_MAX_EXTRACTED_TEXT_CHARS)


def html_to_text(html: str) -> str:
    """Strip tags from HTML and collapse whitespace safely within size bounds."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html[:_MAX_PART_BYTES])
    extractor.close()
    return extractor.text()


def _decode_part_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        bounded = payload[:_MAX_PART_BYTES]
        charset = part.get_content_charset() or "utf-8"
        try:
            return bounded.decode(charset, errors="replace")
        except LookupError:
            return bounded.decode("utf-8", errors="replace")
    if isinstance(payload, str):
        return payload[:_MAX_PART_BYTES]
    return str(part.get_payload() or "")[:_MAX_PART_BYTES]


def _iter_text_parts(message: Message) -> list[tuple[str, str]]:
    """Return ``(content_type, body)`` pairs for non-attachment text parts (bounded)."""
    parts: list[tuple[str, str]] = []
    if message.is_multipart():
        walked = 0
        for part in message.walk():
            walked += 1
            if walked > _MAX_MIME_PARTS:
                break
            if part.is_multipart():
                continue
            disposition = (part.get_content_disposition() or "").lower()
            if disposition == "attachment":
                continue
            content_type = (part.get_content_type() or "").lower()
            if content_type in {"text/html", "text/plain"}:
                parts.append((content_type, _decode_part_payload(part)))
        return parts

    content_type = (message.get_content_type() or "").lower()
    if content_type in {"text/html", "text/plain"}:
        parts.append((content_type, _decode_part_payload(message)))
    elif not content_type or content_type == "text/plain":
        # Some minimal fixtures omit Content-Type; treat body as plain text.
        parts.append(("text/plain", _decode_part_payload(message)))
    return parts


def _text_from_message(message: Message) -> str:
    parts = _iter_text_parts(message)
    html_bodies = [body for ctype, body in parts if ctype == "text/html" and body.strip()]
    if html_bodies:
        return html_to_text(html_bodies[0])
    plain_bodies = [body for ctype, body in parts if ctype == "text/plain" and body.strip()]
    if plain_bodies:
        return sanitize_untrusted_text(plain_bodies[0], max_len=_MAX_EXTRACTED_TEXT_CHARS)
    return ""


def extract_email_text(content: bytes | str) -> str:
    """Prefer ``text/html`` (stripped), else ``text/plain``, from MIME or raw text.

    Args:
        content: Raw MIME bytes (GmailSource) or a string body / MIME text.

    Returns:
        Normalized, sanitized visible text suitable for regex templates.
    """
    message: Message | None = None
    if isinstance(content, bytes):
        if content.strip():
            message = BytesParser(policy=policy.default).parsebytes(content[: _MAX_PART_BYTES * 4])
    else:
        stripped = content.strip()[:_MAX_PART_BYTES]
        if not stripped:
            message = None
        elif stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
            return html_to_text(stripped)
        elif "\n" in stripped and ("content-type:" in stripped.lower() or stripped.lower().startswith("from:")):
            message = Parser(policy=policy.default).parsestr(stripped)
        else:
            return sanitize_untrusted_text(stripped, max_len=_MAX_EXTRACTED_TEXT_CHARS)

    if message is None:
        return ""
    return _text_from_message(message)


def sender_address(metadata_sender: str | None, content: bytes | str) -> str:
    """Extract the verified RFC 5322 addr-spec from Gmail metadata or MIME headers.

    Never returns display-name text so spoofed names like
    ``"Nu <nu@nu.com.co>" <attacker@evil.com>`` cannot impersonate a bank.
    """
    if metadata_sender:
        return extract_sender_addr(metadata_sender)
    if isinstance(content, bytes):
        if not content:
            return ""
        message = BytesParser(policy=policy.default).parsebytes(content[: _MAX_PART_BYTES * 4])
    else:
        if "from:" not in content.lower():
            return ""
        message = Parser(policy=policy.default).parsestr(content[:_MAX_PART_BYTES])
    return extract_sender_addr(message.get("From"))


def subject_line(metadata_subject: str | None, content: bytes | str) -> str:
    """Best-effort sanitized Subject from Gmail metadata or MIME headers."""
    if metadata_subject:
        return sanitize_untrusted_text(metadata_subject, max_len=512)
    if isinstance(content, bytes):
        if not content:
            return ""
        message = BytesParser(policy=policy.default).parsebytes(content[: _MAX_PART_BYTES * 4])
    else:
        if "subject:" not in content.lower():
            return ""
        message = Parser(policy=policy.default).parsestr(content[:_MAX_PART_BYTES])
    return sanitize_untrusted_text(message.get("Subject") or "", max_len=512)


__all__ = [
    "extract_email_text",
    "html_to_text",
    "sender_address",
    "subject_line",
]
