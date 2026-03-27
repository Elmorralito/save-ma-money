"""Unit tests for ``AccountsRepository`` (``papita_txnsmodel.access.accounts.repository``).

Validates the singleton metaclass, ``__expected_dto_type__`` wiring to ``AccountsDTO``,
inheritance from ``OwnedTableRepository``, and owner-guard behavior on owned-table
operations. Database access is avoided by patching instance ``run_query`` for
non-decorated call paths and by patching ``SQLDatabaseConnector.connected`` plus
``Session`` for decorated repository methods so no real engine or network is used.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlmodel import Session

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.accounts import Accounts
from papita_txnsmodel.utils.classutils import MetaSingleton


@pytest.fixture(autouse=True)
def clear_accounts_repository_singleton() -> None:
    """Remove ``AccountsRepository`` from the metaclass cache so each test gets a fresh instance.

    Yields:
        None: Control returns to the test, then the class is evicted again for isolation.
    """
    MetaSingleton._instances.pop(AccountsRepository, None)
    yield
    MetaSingleton._instances.pop(AccountsRepository, None)


@pytest.fixture
def patch_connector_session_context() -> None:
    """Make ``SQLDatabaseConnector.connect`` open a no-op session so decorated methods run.

    Patches ``connected`` to succeed without a real engine and replaces ``Session`` with a
    context manager that yields a throwaway object; tests pass ``_testing_=True`` and a
    mock ``_db_session`` into decorated calls.

    Yields:
        None: Scope ends after the test; patches are stopped automatically.
    """
    with patch.object(SQLDatabaseConnector, "connected", return_value=True), patch(
        "papita_txnsmodel.database.connector.Session"
    ) as mock_session_cls:
        ctx = MagicMock()
        mock_session_cls.return_value = ctx
        ctx.__enter__.return_value = MagicMock()
        ctx.__exit__.return_value = None
        yield


def test_accounts_repository_expected_dto_type_is_accounts_dto() -> None:
    """Assert the repository declares ``AccountsDTO`` as its expected DTO type attribute."""
    assert AccountsRepository.__expected_dto_type__ is AccountsDTO


def test_accounts_repository_metasingleton_returns_same_instance() -> None:
    """Check that repeated instantiation returns the same object (``MetaSingleton``)."""
    first = AccountsRepository()
    second = AccountsRepository()
    assert first is second


def test_accounts_repository_subclasses_owned_table_repository() -> None:
    """Verify structural inheritance so account access enforces owned-table contracts."""
    assert issubclass(AccountsRepository, OwnedTableRepository)
    assert isinstance(AccountsRepository(), OwnedTableRepository)


def test_get_records_without_owner_raises_value_error() -> None:
    """Reject ``get_records`` when ``owner`` is omitted (owned-table guard)."""
    repo = AccountsRepository()
    with pytest.raises(ValueError, match="Owner is required for get_records"):
        repo.get_records(dto_type=AccountsDTO)


@pytest.fixture
def sample_users_dto() -> UsersDTO:
    """Provide a valid ``UsersDTO`` because ``_get_owner_filter`` reads ``owner.id`` (not bare UUIDs).

    Returns:
        UsersDTO: Minimal user row satisfying field validators.
    """
    return UsersDTO(username="testuser", email="test@host.paprika", password="Abcd1234!")


def test_get_records_with_owner_calls_run_query_with_empty_result(sample_users_dto: UsersDTO) -> None:
    """Ensure owner-scoped ``get_records`` delegates to ``run_query`` without touching a real DB.

    Args:
        sample_users_dto: Owner passed into ``get_records``; base code uses ``owner.id`` for the filter.
    """
    repo = AccountsRepository()
    repo.run_query = MagicMock(return_value=pd.DataFrame([]))
    result = repo.get_records(dto_type=AccountsDTO, owner=sample_users_dto)
    assert result.empty
    repo.run_query.assert_called_once()


def test_get_records_from_attributes_without_owner_raises_value_error() -> None:
    """Reject ``get_records_from_attributes`` when ``owner`` is missing."""
    repo = AccountsRepository()
    dto = AccountsDTO(
        owner_id=uuid.uuid4(),
        name="Acct",
        description="Desc",
        tags=["t"],
        start_ts=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_ts=None,
    )
    with pytest.raises(ValueError, match="Owner is required for get_records_from_attributes"):
        repo.get_records_from_attributes(dto)


def test_get_owner_filter_matches_owner_id_on_accounts_dao() -> None:
    """Confirm ``_get_owner_filter`` compares ``Accounts.owner_id`` to ``owner.id`` (bind parameter)."""
    repo = AccountsRepository()
    owner = SimpleNamespace(id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
    flt = repo._get_owner_filter(owner, Accounts)
    assert "owner_id" in str(flt).lower()
    assert getattr(flt.right, "value", object()) == owner.id


@pytest.mark.parametrize(
    "method_name, call_kwargs",
    [
        ("hard_delete_records", {"dto_type": AccountsDTO}),
        ("soft_delete_records", {"dto_type": AccountsDTO}),
    ],
    ids=["hard_delete", "soft_delete"],
)
def test_decorated_delete_methods_require_owner(
    patch_connector_session_context: None,
    mock_session: MagicMock,
    method_name: str,
    call_kwargs: dict,
) -> None:
    """Raise ``ValueError`` on decorated delete helpers when ``owner`` is not supplied.

    Uses ``_testing_`` and a mocked ``Session`` so the connector never opens a real database.

    Args:
        patch_connector_session_context: Ensures the connect decorator does not require a live engine.
        mock_session: SQLModel session double passed through ``_db_session``.
        method_name: Repository method under test.
        call_kwargs: Keyword arguments besides ``owner`` / session overrides.
    """
    repo = AccountsRepository()
    method = getattr(repo, method_name)
    with pytest.raises(ValueError, match="Owner is required"):
        method(
            **call_kwargs,
            _testing_=True,
            _db_session=mock_session,
        )


@pytest.fixture
def mock_session() -> MagicMock:
    """Provide a lightweight ``Session`` stand-in for decorated repository entrypoints.

    Returns:
        MagicMock: Object accepted as ``_db_session`` when ``_testing_`` is true.
    """
    session = MagicMock(spec=Session)
    exec_result = MagicMock()
    exec_result.all.return_value = []
    session.exec.return_value = exec_result
    return session


def test_upsert_record_without_owner_raises_value_error(
    patch_connector_session_context: None,
    mock_session: MagicMock,
) -> None:
    """Require ``owner`` for ``upsert_record`` before any persistence logic runs.

    Args:
        patch_connector_session_context: Satisfies the connect decorator without a real engine.
        mock_session: Injected session double for the decorated call.
    """
    start_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    dto = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Checking",
        description="Primary",
        tags=["checking"],
        start_ts=start_ts,
        end_ts=None,
    )
    repo = AccountsRepository()
    with pytest.raises(ValueError, match="Owner is required for upsert_record"):
        repo.upsert_record(dto, _testing_=True, _db_session=mock_session)
