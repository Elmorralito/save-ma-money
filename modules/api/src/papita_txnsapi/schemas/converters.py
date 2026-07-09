"""Enum slug converters — API lowercase JSON ↔ PostgreSQL uppercase enums."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

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
