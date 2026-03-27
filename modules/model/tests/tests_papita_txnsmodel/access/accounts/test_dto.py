"""Unit tests for ``AccountsDTO`` (``papita_txnsmodel.access.accounts.dto``).

Covers temporal validation for ``start_ts`` / ``end_ts``, ``__dao_type__`` wiring to
``Accounts``, ``from_dao`` / ``to_dao`` conversion using in-memory SQLModel instances
only (no database engine or session), and delegation of ``standardized_dataframe`` to
``datautils.standardize_dataframe`` via ``unittest.mock.patch``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.accounts import Accounts


@pytest.fixture
def sample_owner_id() -> uuid.UUID:
    """Provide a deterministic ``owner_id`` for constructing valid ``AccountsDTO`` rows.

    Returns:
        uuid.UUID: Fixed owner identifier reused across tests for stable assertions.
    """
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def minimal_accounts_kwargs(sample_owner_id: uuid.UUID) -> dict:
    """Provide minimal valid ``CoreTableDTO`` and ``OwnedTableDTO`` fields for accounts.

    Args:
        sample_owner_id: Owner UUID injected by pytest.

    Returns:
        dict: Keyword arguments accepted by ``AccountsDTO`` besides timestamps.
    """
    return {
        "owner_id": sample_owner_id,
        "name": "Checking",
        "description": "Primary checking account",
        "tags": ["checking"],
    }


def test_accounts_dto_dao_type_is_accounts() -> None:
    """Check that ``AccountsDTO.__dao_type__`` references the ``Accounts`` SQLModel class."""
    assert AccountsDTO.__dao_type__ is Accounts


def test_accounts_dto_construct_with_end_after_start(
    minimal_accounts_kwargs: dict,
) -> None:
    """Build ``AccountsDTO`` when ``end_ts`` is strictly after ``start_ts``.

    Args:
        minimal_accounts_kwargs: Valid name, description, tags, and ``owner_id``.
    """
    start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(days=1)
    dto = AccountsDTO(**minimal_accounts_kwargs, start_ts=start_ts, end_ts=end_ts)
    assert dto.start_ts == start_ts
    assert dto.end_ts == end_ts


def test_accounts_dto_end_ts_none_accepted(minimal_accounts_kwargs: dict) -> None:
    """Allow ``end_ts=None`` so active accounts skip the end-after-start constraint.

    Args:
        minimal_accounts_kwargs: Valid base fields for ``AccountsDTO`` construction.
    """
    start_ts = datetime(2025, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    dto = AccountsDTO(**minimal_accounts_kwargs, start_ts=start_ts, end_ts=None)
    assert dto.end_ts is None


@pytest.mark.parametrize(
    "end_offset",
    [timedelta(seconds=0), timedelta(days=-1)],
    ids=["equal_to_start", "before_start"],
)
def test_accounts_dto_end_ts_not_after_start_raises_value_error(
    minimal_accounts_kwargs: dict,
    end_offset: timedelta,
) -> None:
    """Raise ``ValueError`` when ``end_ts`` is equal to or earlier than ``start_ts``.

    Args:
        minimal_accounts_kwargs: Valid base fields for ``AccountsDTO`` construction.
        end_offset: Delta applied to ``start_ts`` to produce an invalid ``end_ts``.
    """
    start_ts = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = start_ts + end_offset
    with pytest.raises(ValueError, match="end_ts must be after start_ts"):
        AccountsDTO(**minimal_accounts_kwargs, start_ts=start_ts, end_ts=end_ts)


def test_accounts_dto_from_dao_success(minimal_accounts_kwargs: dict) -> None:
    """Convert a fully populated in-memory ``Accounts`` row into ``AccountsDTO``.

    Args:
        minimal_accounts_kwargs: Reused name, description, tags, and ``owner_id`` values.
    """
    start_ts = datetime(2024, 6, 15, 8, 30, 0, tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(hours=2)
    account_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    dao = Accounts(
        id=account_id,
        name=minimal_accounts_kwargs["name"],
        description=minimal_accounts_kwargs["description"],
        tags=list(minimal_accounts_kwargs["tags"]),
        owner_id=minimal_accounts_kwargs["owner_id"],
        start_ts=start_ts,
        end_ts=end_ts,
    )
    dto = AccountsDTO.from_dao(dao)
    assert dto.id == account_id
    assert dto.name == minimal_accounts_kwargs["name"]
    assert dto.start_ts == start_ts
    assert dto.end_ts == end_ts
    assert dto.owner_id == minimal_accounts_kwargs["owner_id"]


def test_accounts_dto_from_dao_raises_type_error_for_wrong_dao() -> None:
    """Reject non-``Accounts`` objects passed to ``from_dao`` with ``TypeError``."""
    wrong = MagicMock()
    with pytest.raises(TypeError, match="Unsupported DAO type"):
        AccountsDTO.from_dao(wrong)


def test_accounts_dto_to_dao_returns_accounts_instance(
    minimal_accounts_kwargs: dict,
) -> None:
    """Serialize a DTO to an ``Accounts`` instance using ``model_dump`` (no database).

    Args:
        minimal_accounts_kwargs: Valid base fields for ``AccountsDTO`` construction.
    """
    start_ts = datetime(2023, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    dto = AccountsDTO(**minimal_accounts_kwargs, start_ts=start_ts, end_ts=None)
    dao = dto.to_dao()
    assert isinstance(dao, Accounts)
    assert dao.name == minimal_accounts_kwargs["name"]
    assert dao.owner_id == minimal_accounts_kwargs["owner_id"]
    assert dao.start_ts == start_ts


@patch("papita_txnsmodel.access.base.dto.datautils.standardize_dataframe")
def test_accounts_dto_standardized_dataframe_delegates(
    mock_standardize: MagicMock,
) -> None:
    """Assert ``AccountsDTO.standardized_dataframe`` calls the shared dataframe helper.

    Args:
        mock_standardize: Patched ``standardize_dataframe`` used to observe the call.
    """
    frame = pd.DataFrame({"id": [uuid.uuid4()], "name": ["Checking"]})
    expected = pd.DataFrame({"id": [uuid.uuid4()], "name": ["Checking"]})
    mock_standardize.return_value = expected
    result = AccountsDTO.standardized_dataframe(frame, drops=["deleted_at"], by_alias=True, extra="kw")
    assert result.equals(expected)
    mock_standardize.assert_called_once_with(
        AccountsDTO, frame, drops=["deleted_at"], by_alias=True, extra="kw"
    )
