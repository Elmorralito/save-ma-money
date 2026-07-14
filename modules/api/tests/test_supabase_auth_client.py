"""Unit tests for Supabase Auth client helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from papita_txnsapi.core.supabase_auth import supabase_sign_in, supabase_sign_up


def test_supabase_sign_up_maps_user_and_metadata() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=None,
    )
    result = supabase_sign_up(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        username="alice01",
        client=client,
    )
    assert result.user_id == subject
    assert result.email == "a@example.local"
    assert result.access_token is None
    client.auth.sign_up.assert_called_once()
    payload = client.auth.sign_up.call_args.args[0]
    assert payload["options"]["data"]["username"] == "alice01"


def test_supabase_sign_in_requires_access_token() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=SimpleNamespace(access_token="tok", expires_in=120),
    )
    result = supabase_sign_in(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        client=client,
    )
    assert result.access_token == "tok"
    assert result.expires_in == 120
