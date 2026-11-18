"""Enum slug converters — API lowercase JSON ↔ PostgreSQL uppercase enums.

The REST contract exposes enum values as lowercase slugs (e.g. ``checking``,
``expense``). The model layer and database store uppercase ``Enum`` members
(e.g. ``AccountKind.CHECKING``). These helpers normalize in both directions and
raise descriptive ``ValueError`` messages when a slug is unknown.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from papita_txnsmodel.model.enums import (
    AccountKind,
    CategoryKind,
    IngestionRunStatus,
    LedgerSide,
    TransactionKind,
    TransactionStatus,
)

E = TypeVar("E", bound=Enum)


def api_slug_to_enum(enum_type: type[E], slug: str) -> E:
    """Convert an API lowercase slug to a model/DB enum member.

    Args:
        enum_type: Target enum class (e.g. ``AccountKind``).
        slug: Lowercase slug from JSON (e.g. ``checking``).

    Returns:
        Matching enum member (e.g. ``AccountKind.CHECKING``).

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
    """Convert a model/DB enum member to an API lowercase slug.

    Args:
        value: Enum member whose ``value`` is the database representation.

    Returns:
        Lowercase slug suitable for JSON responses.
    """
    return value.value.lower()


def parse_account_kind(slug: str) -> AccountKind:
    """Parse an API ``account_kind`` slug to ``AccountKind``.

    Args:
        slug: Lowercase account kind from request JSON.

    Returns:
        Corresponding ``AccountKind`` member.

    Raises:
        ValueError: When the slug is not a valid account kind.
    """
    return api_slug_to_enum(AccountKind, slug)


def parse_ledger_side(slug: str) -> LedgerSide:
    """Parse an API ``ledger_side`` slug to ``LedgerSide``.

    Args:
        slug: Lowercase ledger side from request JSON (e.g. ``asset``).

    Returns:
        Corresponding ``LedgerSide`` member.

    Raises:
        ValueError: When the slug is not a valid ledger side.
    """
    return api_slug_to_enum(LedgerSide, slug)


def parse_category_kind(slug: str) -> CategoryKind:
    """Parse an API ``category_type`` slug to ``CategoryKind``.

    Args:
        slug: Lowercase category type from request JSON.

    Returns:
        Corresponding ``CategoryKind`` member.

    Raises:
        ValueError: When the slug is not a valid category kind.
    """
    return api_slug_to_enum(CategoryKind, slug)


def parse_transaction_kind(slug: str) -> TransactionKind:
    """Parse an API ``transaction_type`` slug to ``TransactionKind``.

    Args:
        slug: Lowercase transaction type from request JSON.

    Returns:
        Corresponding ``TransactionKind`` member.

    Raises:
        ValueError: When the slug is not a valid transaction kind.
    """
    return api_slug_to_enum(TransactionKind, slug)


def parse_transaction_status(slug: str) -> TransactionStatus:
    """Parse an API ``status`` slug to ``TransactionStatus``.

    Args:
        slug: Lowercase status from request JSON or query params.

    Returns:
        Corresponding ``TransactionStatus`` member.

    Raises:
        ValueError: When the slug is not a valid transaction status.
    """
    return api_slug_to_enum(TransactionStatus, slug)


def parse_ingestion_run_status(slug: str) -> IngestionRunStatus:
    """Parse an API ingestion run ``status`` slug to ``IngestionRunStatus``.

    Args:
        slug: Lowercase status from request JSON or query params
            (e.g. ``succeeded``, ``partial``).

    Returns:
        Corresponding ``IngestionRunStatus`` member.

    Raises:
        ValueError: When the slug is not a valid ingestion run status.
    """
    return api_slug_to_enum(IngestionRunStatus, slug)
