"""Unit tests for postgres_gate URL helpers."""

from __future__ import annotations

from postgres_gate import is_supabase_pooler_url


def test_is_supabase_pooler_url_accepts_pooler_host() -> None:
    assert is_supabase_pooler_url("postgresql://user:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres")


def test_is_supabase_pooler_url_accepts_explicit_port() -> None:
    assert is_supabase_pooler_url("postgresql://user:pass@db.example.com:6543/postgres")


def test_is_supabase_pooler_url_rejects_substring_in_path() -> None:
    assert not is_supabase_pooler_url("postgresql://user:pass@localhost:5432/pooler.supabase.com")


def test_is_supabase_pooler_url_rejects_standard_postgres() -> None:
    assert not is_supabase_pooler_url("postgresql://user:pass@localhost:5432/postgres")
