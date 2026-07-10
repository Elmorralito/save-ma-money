"""Enum slug converters — API lowercase JSON ↔ PostgreSQL uppercase enums."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide

E = TypeVar("E", bound=Enum)


def api_slug_to_enum(enum_type: type[E], slug: str) -> E:
    """Convert an API lowercase slug to a model/DB enum member.

    Args:
        enum_type: Target enum class (e.g. ``TransactionKind``).
        slug: Lowercase slug from JSON (e.g. ``expense``).

    Returns:
        Matching enum member (e.g. ``TransactionKind.EXPENSE``).

    Raises:
        ValueError: When the slug does not match any enum value.
    """
    normalized = slug.strip().upper()
    try:
        return enum_type(normalized)
    except ValueError as exc:
        valid = ", ".join(member.value.lower() for member in enum_type)
        raise ValueError(f"Invalid value '{slug}' for {enum_type.__name__}. Expected one of: {valid}") from exc


def enum_to_api_slug(value: Enum) -> str:
    """Convert a model/DB enum member to an API lowercase slug."""
    return value.value.lower()


def parse_account_kind(slug: str) -> AccountKind:
    """Parse an API account_kind slug to ``AccountKind``."""
    return api_slug_to_enum(AccountKind, slug)


def parse_ledger_side(slug: str) -> LedgerSide:
    """Parse an API ledger_side slug to ``LedgerSide``."""
    return api_slug_to_enum(LedgerSide, slug)


def parse_category_kind(slug: str) -> CategoryKind:
    """Parse an API category_type slug to ``CategoryKind``."""
    return api_slug_to_enum(CategoryKind, slug)
