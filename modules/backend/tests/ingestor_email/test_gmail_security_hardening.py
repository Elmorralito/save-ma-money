"""Security hardening tests for Gmail ingestion, MIME parsing, OAuth encryption, and ReDoS guards."""

from __future__ import annotations

import base64
import hashlib
import uuid
from email.message import EmailMessage

import pytest
from cryptography.fernet import Fernet

from papita_ingestor_core.runner.ingestion_runner import _redact_text
from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.parsers.mime import extract_email_text, html_to_text, sender_address
from papita_ingestor_email.parsers.nu import NuParser
from papita_ingestor_email.parsers.security import (
    extract_sender_addr,
    redact_sensitive_text,
    sanitize_untrusted_text,
    verify_email_authentication,
)
from papita_ingestor_email.sources.gmail import MAX_RAW_MESSAGE_BYTES, GmailSource
from papita_txnsapi.config.settings import Settings
from papita_txnsapi.routers.v1.ingestion import _fernet_for_settings
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.services.ingestion_status import _validate_parsing_rules


def _encode_mime(msg: EmailMessage) -> str:
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def test_display_name_spoofing_cannot_impersonate_bank() -> None:
    spoofed_from = '"Nu <nu@nu.com.co>" <attacker@evil.example>'
    assert extract_sender_addr(spoofed_from) == "attacker@evil.example"
    assert sender_address(spoofed_from, b"") == "attacker@evil.example"

    record = RawRecord(
        source_id="gmail",
        ingestion_source=IngestionSource.EMAIL,
        source_ref="spoof-1",
        content="Tu pago fue de $1.975.723,00".encode(),
        metadata={"sender": spoofed_from, "subject": "¡Ya entró tu pago!"},
    )
    assert NuParser().can_parse(record) is False


def test_gmail_source_rejects_failed_dkim_spf_authentication() -> None:
    msg = EmailMessage()
    msg["From"] = "Nu <nu@nu.com.co>"
    msg["To"] = "victim@example.com"
    msg["Subject"] = "¡Ya entró tu pago!"
    msg["Authentication-Results"] = "mx.google.com; dkim=fail header.d=nu.com.co; spf=fail; dmarc=fail"
    msg.set_content("Tu pago fue de $1.975.723,00")

    source = GmailSource()
    record = source._to_raw_record({"id": "msg-spoof", "raw": _encode_mime(msg), "snippet": "sensitive"})
    assert record is None


def test_gmail_source_strips_unsafe_headers_and_snippet() -> None:
    msg = EmailMessage()
    msg["From"] = "Nu <nu@nu.com.co>"
    msg["To"] = "victim@example.com"
    msg["Delivered-To"] = "victim@example.com"
    msg["Received"] = "from internal.bank.local [10.0.0.1]"
    msg["X-Secret-Tracker"] = "track-123"
    msg["Subject"] = "¡Ya entró tu pago!"
    msg["Authentication-Results"] = "mx.google.com; dkim=pass header.d=nu.com.co; spf=pass; dmarc=pass"
    msg.set_content("Tu pago fue de $1.975.723,00")

    source = GmailSource()
    record = source._to_raw_record({"id": "msg-ok", "raw": _encode_mime(msg), "snippet": "DO NOT STORE THIS SNIPPET"})
    assert record is not None
    assert "snippet" not in record.metadata
    assert record.metadata["sender"] == "nu@nu.com.co"
    header_keys = {k.lower() for k in record.metadata["headers"]}
    assert "received" not in header_keys
    assert "delivered-to" not in header_keys
    assert "to" not in header_keys
    assert "x-secret-tracker" not in header_keys
    assert "authentication-results" in header_keys


def test_gmail_source_skips_oversized_messages() -> None:
    oversized_b64 = "A" * ((MAX_RAW_MESSAGE_BYTES * 4) // 3 + 128)
    source = GmailSource()
    assert source._to_raw_record({"id": "msg-huge", "raw": oversized_b64}) is None


def test_mime_skips_attachments_and_strips_dangerous_html_and_bidi() -> None:
    msg = EmailMessage()
    msg["From"] = "Nu <nu@nu.com.co>"
    msg["Subject"] = "Alert\u202eSpoof\x00"
    msg.set_content("Plain body")
    msg.add_alternative(
        "<html><head><title>Hidden</title></head><body>"
        "<script>alert(1)</script><svg>bad</svg><template>nope</template>"
        "<p>Tu pago fue de $50.000,00\u202e</p></body></html>",
        subtype="html",
    )
    msg.add_attachment(b"%PDF-1.7 secret attachment bytes", maintype="application", subtype="pdf", filename="stmt.pdf")

    extracted = extract_email_text(msg.as_bytes())
    assert "alert(1)" not in extracted
    assert "Hidden" not in extracted
    assert "nope" not in extracted
    assert "secret attachment" not in extracted
    assert "\u202e" not in extracted
    assert "Tu pago fue de $50.000,00" in extracted
    assert html_to_text("<style>body{display:none}</style><p>Safe</p>") == "Safe"
    assert sanitize_untrusted_text("ok\x00\u202etext") == "oktext"


def test_redaction_masks_card_pans_and_oauth_tokens() -> None:
    raw = "Failed Bearer ya29.a0AfH6SMB1234567890abcdef and refresh 1//0gAbCdEfGhIjKlMnOpQrStUv on card 4532 1234 5678 9012"
    redacted = redact_sensitive_text(raw)
    assert "ya29." not in redacted
    assert "1//0g" not in redacted
    assert "4532 1234 5678" not in redacted
    assert "****9012" in redacted
    assert "[REDACTED_TOKEN]" in redacted

    runner_redacted = _redact_text(raw)
    assert "ya29." not in runner_redacted
    assert "****9012" in runner_redacted


@pytest.mark.parametrize("bad_regex", ["(a+)+$", "(.*)*foo", r"(\d+)\1", r"(?<=\$)\d+"])
def test_parsing_rules_reject_redos_patterns(bad_regex: str) -> None:
    with pytest.raises(ValueError, match="nested quantifiers|backreferences|lookbehinds"):
        _validate_parsing_rules(
            [
                {
                    "name": "Evil regex",
                    "parser_mode": "custom_regex",
                    "amount_regex": bad_regex,
                    "currency": "COP",
                }
            ]
        )


def test_fernet_hkdf_encrypts_and_supports_legacy_decryption() -> None:
    secret = "test-jwt-secret-" + uuid.uuid4().hex
    settings = Settings(JWT_SECRET_KEY=secret, GMAIL_TOKEN_ENCRYPTION_KEY="dedicated-gmail-enc-key-" + uuid.uuid4().hex)
    multi = _fernet_for_settings(settings)

    token = "1//0g_test_refresh_token_value"
    ct = multi.encrypt(token.encode("utf-8"))
    assert multi.decrypt(ct).decode("utf-8") == token

    # Verify legacy SHA-256(JWT_SECRET_KEY) ciphertexts still decrypt during rotation
    legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest()))
    legacy_ct = legacy.encrypt(token.encode("utf-8"))
    assert multi.decrypt(legacy_ct).decode("utf-8") == token


def test_verify_email_authentication_cases() -> None:
    assert verify_email_authentication({}) == (True, "no_auth_header")
    assert verify_email_authentication({"Authentication-Results": "dkim=pass; spf=pass"})[0] is True
    assert verify_email_authentication({"Authentication-Results": "dkim=fail; spf=fail; dmarc=fail"})[0] is False
