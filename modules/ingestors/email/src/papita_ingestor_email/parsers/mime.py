"""MIME / HTML helpers for email bank parsers (PPT-081 / #175)."""

from __future__ import annotations

import re
from email import policy
from email.message import Message
from email.parser import BytesParser, Parser
from html.parser import HTMLParser

_WHITESPACE_RE = re.compile(r"\s+")


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text from HTML, ignoring script/style bodies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def text(self) -> str:
        return _WHITESPACE_RE.sub(" ", "".join(self._chunks)).strip()


def html_to_text(html: str) -> str:
    """Strip tags from HTML and collapse whitespace."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    extractor.close()
    return extractor.text()


def _decode_part_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    if isinstance(payload, str):
        return payload
    return str(part.get_payload() or "")


def _iter_text_parts(message: Message) -> list[tuple[str, str]]:
    """Return ``(content_type, body)`` pairs for text parts (depth-first)."""
    parts: list[tuple[str, str]] = []
    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
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
        return _WHITESPACE_RE.sub(" ", plain_bodies[0]).strip()
    return ""


def extract_email_text(content: bytes | str) -> str:
    """Prefer ``text/html`` (stripped), else ``text/plain``, from MIME or raw text.

    Args:
        content: Raw MIME bytes (GmailSource) or a string body / MIME text.

    Returns:
        Normalized visible text suitable for regex templates.
    """
    message: Message | None = None
    if isinstance(content, bytes):
        if content.strip():
            message = BytesParser(policy=policy.default).parsebytes(content)
    else:
        stripped = content.strip()
        if not stripped:
            message = None
        elif stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
            return html_to_text(stripped)
        elif "\n" in stripped and ("content-type:" in stripped.lower() or stripped.lower().startswith("from:")):
            message = Parser(policy=policy.default).parsestr(stripped)
        else:
            return _WHITESPACE_RE.sub(" ", stripped)

    if message is None:
        return ""
    return _text_from_message(message)


def sender_address(metadata_sender: str | None, content: bytes | str) -> str:
    """Best-effort From address from Gmail metadata or MIME headers."""
    if metadata_sender:
        return metadata_sender.strip()
    if isinstance(content, bytes):
        if not content:
            return ""
        message = BytesParser(policy=policy.default).parsebytes(content)
    else:
        if "from:" not in content.lower():
            return ""
        message = Parser(policy=policy.default).parsestr(content)
    return (message.get("From") or "").strip()


def subject_line(metadata_subject: str | None, content: bytes | str) -> str:
    """Best-effort Subject from Gmail metadata or MIME headers."""
    if metadata_subject:
        return metadata_subject.strip()
    if isinstance(content, bytes):
        if not content:
            return ""
        message = BytesParser(policy=policy.default).parsebytes(content)
    else:
        if "subject:" not in content.lower():
            return ""
        message = Parser(policy=policy.default).parsestr(content)
    return (message.get("Subject") or "").strip()


__all__ = [
    "extract_email_text",
    "html_to_text",
    "sender_address",
    "subject_line",
]
