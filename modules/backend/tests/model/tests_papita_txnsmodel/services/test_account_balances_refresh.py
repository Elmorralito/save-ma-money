"""Tests for account_balances materialized view refresh."""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.transactions import TransactionsService

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def owner() -> UsersDTO:
    """Tenant user for owned-table service calls."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="user_a_test",
        email="user_a@example.local",
        password=_VALID_PASSWORD,
        auth_provider="local",
    )


class TestTransactionBalanceRefresh:
    """Posted transaction writes opt into MV refresh; default is off."""

    def test_upsert_records_skips_refresh_by_default(self, owner: UsersDTO):
        """Default refresh_balances=False avoids N× MV refresh on bulk paths."""
        with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
            service = TransactionsService()
            service._repository = MagicMock()

        mappings = pd.DataFrame([{"id": "00000000-0000-0000-0000-000000000001"}])
        with (
            patch(
                "papita_txnsmodel.services.base.BaseService.upsert_records",
                return_value=mappings,
            ),
            patch(
                "papita_txnsmodel.services.transactions.refresh_balance_materialized_views",
            ) as mock_refresh,
        ):
            service.upsert_records(df=mappings, owner=owner)
            mock_refresh.assert_not_called()

    def test_upsert_records_refreshes_when_enabled(self, owner: UsersDTO):
        """Callers can opt into MV refresh after a write batch."""
        with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
            service = TransactionsService()
            service._repository = MagicMock()

        mappings = pd.DataFrame([{"id": "00000000-0000-0000-0000-000000000001"}])
        with (
            patch(
                "papita_txnsmodel.services.base.BaseService.upsert_records",
                return_value=mappings,
            ),
            patch(
                "papita_txnsmodel.services.transactions.refresh_balance_materialized_views",
            ) as mock_refresh,
        ):
            service.upsert_records(df=mappings, owner=owner, refresh_balances=True)
            mock_refresh.assert_called_once_with(service.connector, concurrently=False)

    def test_refresh_balance_views_helper(self, owner: UsersDTO):
        """Explicit helper refreshes MVs once after deferred write batches."""
        del owner
        with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
            service = TransactionsService()
        with patch(
            "papita_txnsmodel.services.transactions.refresh_balance_materialized_views",
        ) as mock_refresh:
            service.refresh_balance_views(concurrently=True)
            mock_refresh.assert_called_once_with(service.connector, concurrently=True)

    def test_refresh_balance_materialized_views_refreshes_all_layers(self):
        """Central refresh helper updates account + owner period views."""
        connector = MagicMock()
        with (
            patch(
                "papita_txnsmodel.services.balance_views.AccountBalancesService.model_validate",
            ) as mock_account_factory,
            patch(
                "papita_txnsmodel.services.balance_views.OwnerYearlyBalancesService.model_validate",
            ) as mock_yearly_factory,
            patch(
                "papita_txnsmodel.services.balance_views.OwnerPeriodBalancesService.model_validate",
            ) as mock_period_factory,
        ):
            mock_account = MagicMock()
            mock_yearly = MagicMock()
            mock_period = MagicMock()
            mock_account_factory.return_value = mock_account
            mock_yearly_factory.return_value = mock_yearly
            mock_period_factory.return_value = mock_period

            refresh_balance_materialized_views(connector, concurrently=True)

            mock_account.refresh.assert_called_once_with(concurrently=True)
            mock_yearly.refresh.assert_called_once_with(concurrently=True)
            mock_period.refresh.assert_called_once_with(concurrently=True)

    def test_account_balances_service_exposes_refresh(self):
        """Read service delegates refresh to repository."""
        service = AccountBalancesService()
        repo = MagicMock()
        service._repository = repo
        service.refresh(concurrently=True)
        repo.refresh_materialized_view.assert_called_once_with(concurrently=True)


class TestAccountBalancesPageScopedQuery:
    """Page-scoped balance loads use repository IN filter, not full-tenant reports."""

    def test_get_balances_with_account_ids_uses_repository(self, owner: UsersDTO) -> None:
        """Non-empty account_ids delegates to AccountBalancesRepository."""
        service = AccountBalancesService()
        repo = MagicMock()
        account_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        expected = pd.DataFrame([{"account_id": account_id, "balance": 10.0}])
        repo.get_balances.return_value = expected
        service._repository = repo

        result = service.get_balances(owner=owner, account_ids=[account_id])

        assert result.equals(expected)
        repo.get_balances.assert_called_once_with(owner=owner, account_ids=[account_id])

    def test_get_balances_with_empty_account_ids_skips_query(self, owner: UsersDTO) -> None:
        """Empty account_ids returns an empty frame without hitting the repository."""
        service = AccountBalancesService()
        repo = MagicMock()
        service._repository = repo

        result = service.get_balances(owner=owner, account_ids=[])

        assert getattr(result, "empty", True)
        repo.get_balances.assert_not_called()

    def test_get_balances_rejects_account_id_and_account_ids(self, owner: UsersDTO) -> None:
        """account_id and account_ids are mutually exclusive."""
        service = AccountBalancesService()
        account_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

        with pytest.raises(ValueError, match="account_id or account_ids"):
            service.get_balances(owner=owner, account_id=account_id, account_ids=[account_id])
