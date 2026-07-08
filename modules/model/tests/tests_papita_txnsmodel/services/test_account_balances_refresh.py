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
    )


class TestTransactionBalanceRefresh:
    """Posted transaction upserts should refresh balance materialized views by default."""

    def test_upsert_records_refreshes_balances_by_default(self, owner: UsersDTO):
        """TransactionsService triggers MV refresh after successful upsert."""
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

    def test_upsert_records_skips_refresh_when_disabled(self, owner: UsersDTO):
        """Bulk ingest can defer refresh with refresh_balances=False."""
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
            service.upsert_records(df=mappings, owner=owner, refresh_balances=False)
            mock_refresh.assert_not_called()

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
