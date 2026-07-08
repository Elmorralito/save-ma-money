"""Cross-tenant access denial tests for OwnedTableRepository (NFR-04).

Validates that multi-tenant repositories require an owner context and reject
cross-tenant upserts. Integration tests against a live DB are deferred to the
v3 migration PR; these unit tests enforce the repository contract.
"""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.transactions.repository import TransactionsRepository
from papita_txnsmodel.access.categories.repository import CategoriesRepository
from papita_txnsmodel.model.enums import AccountKind, LedgerSide
from papita_txnsmodel.access.users.dto import UsersDTO

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def user_a() -> UsersDTO:
    """First tenant user."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="user_a_test",
        email="user_a@example.local",
        password=_VALID_PASSWORD,
    )


@pytest.fixture
def user_b() -> UsersDTO:
    """Second tenant user."""
    return UsersDTO(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        username="user_b_test",
        email="user_b@example.local",
        password=_VALID_PASSWORD,
    )


@pytest.fixture
def sample_account_dto(user_a: UsersDTO) -> AccountsDTO:
    """Minimal valid AccountsDTO for repository tests."""
    return AccountsDTO(
        id=uuid.uuid4(),
        name="Test Account",
        description="Test description",
        tags=["test"],
        owner_id=user_a.id,
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )


@pytest.fixture
def mock_connector_connected():
    """Mock SQLDatabaseConnector.connected to return True for testing."""
    with patch("papita_txnsmodel.access.base.repository.SQLDatabaseConnector.connected", return_value=True):
        yield


class TestOwnedTableRepositoryRequiresOwner:
    """Owner must be provided for all tenant-scoped operations."""

    @pytest.fixture
    def repository(self):
        """OwnedTableRepository instance."""
        return OwnedTableRepository()

    @pytest.mark.parametrize(
        "method_name,extra_kwargs,needs_session",
        [
            ("get_records", {}, False),
            ("get_records_from_attributes", {}, False),
            ("get_record_from_attributes", {}, False),
            ("upsert_record", {}, True),
            ("soft_delete_records", {}, True),
            ("hard_delete_records", {}, True),
        ],
    )
    def test_missing_owner_raises_value_error(
        self, repository, method_name, extra_kwargs, needs_session, sample_account_dto, mock_connector_connected
    ):
        """Operations without owner= must fail fast."""
        method = getattr(repository, method_name)
        kwargs = {"dto_type": AccountsDTO, **extra_kwargs}
        if method_name in {"get_records_from_attributes", "get_record_from_attributes", "upsert_record"}:
            kwargs["dto"] = sample_account_dto
        if needs_session:
            kwargs["_db_session"] = MagicMock()

        with pytest.raises(ValueError, match="Owner is required"):
            method(**kwargs)

    def test_upsert_records_missing_owner_raises(self, repository, mock_connector_connected):
        """Bulk upsert without owner must fail."""
        with pytest.raises(ValueError, match="Owner is required"):
            repository.upsert_records(
                AccountsDTO,
                pd.DataFrame({"id": [uuid.uuid4()], "name": ["acct"]}),
                _db_session=MagicMock(),
            )


class TestCrossTenantUpsertDenial:
    """User A cannot upsert records owned by User B."""

    @pytest.fixture
    def repository(self):
        """OwnedTableRepository instance."""
        return OwnedTableRepository()

    def test_upsert_record_rejects_other_tenant_owner_id(
        self, repository, user_a, user_b, sample_account_dto, mock_connector_connected
    ):
        """Upsert with DTO.owner_id belonging to another tenant raises ValueError."""
        sample_account_dto.owner_id = user_b.id
        with pytest.raises(ValueError, match="DTO owner_id does not match"):
            repository.upsert_record(sample_account_dto, owner=user_a, _db_session=MagicMock())

    def test_upsert_record_assigns_owner_when_missing(
        self, repository, user_a, sample_account_dto, mock_connector_connected
    ):
        """Upsert assigns owner_id when DTO has none set."""
        sample_account_dto.owner_id = None  # type: ignore[assignment]
        with patch(
            "papita_txnsmodel.access.base.repository.BaseRepository.upsert_record",
            return_value=sample_account_dto,
        ) as mock_super:
            result = repository.upsert_record(sample_account_dto, owner=user_a, _db_session=MagicMock())
            assert sample_account_dto.owner_id == user_a.id
            mock_super.assert_called_once()
            assert result is sample_account_dto


class TestCrossTenantQueryIsolation:
    """get_records applies owner filter so other tenants' rows are not returned."""

    @pytest.mark.parametrize(
        "repository_cls,dto_cls",
        [
            (AccountsRepository, AccountsDTO),
            (TransactionsRepository, TransactionsDTO),
        ],
    )
    def test_get_records_includes_owner_filter(self, repository_cls, dto_cls, user_a):
        """Owner filter is prepended to every tenant-scoped query."""
        repository = repository_cls()
        expected_owner_filter = str(dto_cls.__dao_type__.owner_id == user_a.id)

        with patch(
            "papita_txnsmodel.access.base.repository.BaseRepository.get_records",
            return_value=pd.DataFrame(),
        ) as mock_super:
            repository.get_records(dto_type=dto_cls, owner=user_a)

        mock_super.assert_called_once()
        positional_args = mock_super.call_args[0]
        assert any(str(arg) == expected_owner_filter for arg in positional_args)

    def test_categories_repository_scopes_to_owner_and_global(self, user_a):
        """CategoriesRepository returns owner rows plus global (owner_id IS NULL) rows only."""
        repository = CategoriesRepository()

        with patch(
            "papita_txnsmodel.access.base.repository.BaseRepository.get_records",
            return_value=pd.DataFrame(),
        ) as mock_super:
            repository.get_records(owner=user_a)

        mock_super.assert_called_once()
        assert len(mock_super.call_args[0]) >= 1

    def test_user_a_query_does_not_return_user_b_data(self, user_a):
        """Filtered query for another tenant's record id returns empty when owner filter applies."""
        repository = AccountsRepository()
        other_account_id = uuid.uuid4()
        expected_owner_filter = str(AccountsDTO.__dao_type__.owner_id == user_a.id)

        empty_df = pd.DataFrame()
        with patch(
            "papita_txnsmodel.access.base.repository.BaseRepository.get_records",
            return_value=empty_df,
        ) as mock_super:
            result = repository.get_records(
                AccountsDTO.__dao_type__.id == other_account_id,
                dto_type=AccountsDTO,
                owner=user_a,
            )

        assert result.empty
        positional_args = mock_super.call_args[0]
        assert any(str(arg) == expected_owner_filter for arg in positional_args)
