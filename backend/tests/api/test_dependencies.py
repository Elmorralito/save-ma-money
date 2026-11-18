"""Tests for shared dependencies and schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.schemas.converters import api_slug_to_enum, enum_to_api_slug
from papita_txnsmodel.model.enums import TransactionKind


class TestPagination:
    """Pagination dependency defaults and bounds."""

    def test_defaults(self) -> None:
        params = get_pagination()
        assert params.skip == 0
        assert params.limit == 100

    def test_limit_max_enforced(self) -> None:
        with pytest.raises(ValidationError):
            PaginationParams(skip=0, limit=501)


class TestEnumConverters:
    """API slug ↔ DB enum mapping."""

    def test_slug_to_enum(self) -> None:
        assert api_slug_to_enum(TransactionKind, "expense") == TransactionKind.EXPENSE

    def test_enum_to_slug(self) -> None:
        assert enum_to_api_slug(TransactionKind.INCOME) == "income"

    def test_invalid_slug_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid value"):
            api_slug_to_enum(TransactionKind, "not-a-kind")
