"""Unit tests for PPT-041 service-layer deliverables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.account_details.dto import BankingAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import (
    AccountKind,
    CategoryKind,
    LedgerSide,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.reports import ReportService
from papita_txnsmodel.services.transactions import TransactionsService

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def owner() -> UsersDTO:
    """Tenant user for service calls."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="user_a_test",
        email="user_a@example.local",
        password=_VALID_PASSWORD,
    )


def _accounts_service() -> AccountsService:
    with patch("papita_txnsmodel.services.accounts.AccountsRepository"):
        service = AccountsService()
        service._repository = MagicMock()
        service.balances_service = MagicMock()
        return service


def _transactions_service() -> TransactionsService:
    with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
        service = TransactionsService()
        service._repository = MagicMock()
        return service


class TestAccountsServiceOrchestration:
    """AccountsService routes extension writes by account_kind."""

    def test_create_account_requires_extension_for_banking_kind(self, owner: UsersDTO):
        """Checking accounts must include banking extension details."""
        service = _accounts_service()
        account = AccountsDTO(
            name="Checking",
            description="Primary",
            owner_id=owner.id,
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
        )
        with patch.object(BaseService, "create", return_value=account):
            with pytest.raises(ValueError, match="requires extension"):
                service.create_account(obj=account, owner=owner)

    def test_create_account_upserts_extension(self, owner: UsersDTO):
        """Extension row is created after the consolidated account row."""
        service = _accounts_service()
        account = AccountsDTO(
            id=uuid.uuid4(),
            name="Checking",
            description="Primary",
            owner_id=owner.id,
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
        )
        extension = BankingAccountDetailsDTO(account_id=account.id, entity="Bank Co")
        with (
            patch.object(BaseService, "create", return_value=account),
            patch(
                "papita_txnsmodel.services.account_details.BankingAccountDetailsService.model_validate",
            ) as mock_factory,
        ):
            extension_service = MagicMock()
            extension_service.create.return_value = extension
            mock_factory.return_value = extension_service
            result = service.create_account(
                obj=account,
                extension={"entity": "Bank Co"},
                owner=owner,
            )
        assert result is account
        extension_service.create.assert_called_once()

    def test_get_balance_delegates_to_balances_service(self, owner: UsersDTO):
        """Account balance reads use AccountBalancesService."""
        service = _accounts_service()
        account_id = uuid.uuid4()
        service.balances_service.get_balance.return_value = MagicMock()
        service.get_balance(owner=owner, account_id=account_id)
        service.balances_service.get_balance.assert_called_once_with(owner=owner, account_id=account_id)


class TestTransactionsServiceTransfers:
    """Transfer helpers enforce TRANSFER semantics."""

    def test_list_transfers_filters_by_kind(self, owner: UsersDTO):
        """list_transfers queries transaction_kind=TRANSFER."""
        service = _transactions_service()
        service._repository.get_records.return_value = pd.DataFrame()
        service.list_transfers(owner=owner)
        assert service._repository.get_records.call_count == 1

    def test_create_transfer_requires_account_legs(self, owner: UsersDTO):
        """Transfers without both account legs are rejected."""
        service = _transactions_service()
        with pytest.raises(ValueError, match="from_account_id and to_account_id"):
            service.create_transfer(
                obj={
                    "transaction_kind": TransactionKind.TRANSFER,
                    "amount": 10.0,
                    "owner_id": owner.id,
                    "from_account_id": uuid.uuid4(),
                },
                owner=owner,
            )

    def test_create_transfer_defaults_pending_status(self, owner: UsersDTO):
        """New transfers default to PENDING until executed."""
        service = _transactions_service()
        transfer = TransactionsDTO(
            owner_id=owner.id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=25.0,
            from_account_id=uuid.uuid4(),
            to_account_id=uuid.uuid4(),
        )
        with patch.object(TransactionsService, "create", return_value=transfer) as mock_create:
            service.create_transfer(obj=transfer, owner=owner)
        submitted = mock_create.call_args.kwargs["obj"]
        assert submitted.status == TransactionStatus.PENDING

    def test_complete_transfer_sets_completed(self, owner: UsersDTO):
        """execute movement sets status=COMPLETED."""
        service = _transactions_service()
        transfer_id = uuid.uuid4()
        transfer = TransactionsDTO(
            id=transfer_id,
            owner_id=owner.id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=25.0,
            from_account_id=uuid.uuid4(),
            to_account_id=uuid.uuid4(),
            status=TransactionStatus.PENDING,
        )
        with (
            patch.object(TransactionsService, "get", return_value=transfer),
            patch.object(TransactionsService, "create", return_value=transfer) as mock_create,
        ):
            service.complete_transfer(transaction_id=transfer_id, owner=owner)
        submitted = mock_create.call_args.kwargs["obj"]
        assert submitted.status == TransactionStatus.COMPLETED

    def test_cancel_sets_cancelled_status(self, owner: UsersDTO):
        """DELETE /movements maps to status=CANCELLED."""
        service = _transactions_service()
        transfer_id = uuid.uuid4()
        transfer = TransactionsDTO(
            id=transfer_id,
            owner_id=owner.id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=25.0,
            from_account_id=uuid.uuid4(),
            to_account_id=uuid.uuid4(),
            status=TransactionStatus.PENDING,
        )
        with (
            patch.object(TransactionsService, "get", return_value=transfer),
            patch.object(TransactionsService, "create", return_value=transfer) as mock_create,
        ):
            service.cancel(transaction_id=transfer_id, owner=owner)
        submitted = mock_create.call_args.kwargs["obj"]
        assert submitted.status == TransactionStatus.CANCELLED

    def test_create_refreshes_balances_by_default(self, owner: UsersDTO):
        """Single create triggers MV refresh like bulk upsert."""
        service = _transactions_service()
        transfer = TransactionsDTO(owner_id=owner.id, transaction_kind=TransactionKind.EXPENSE, amount=5.0)
        with (
            patch("papita_txnsmodel.services.transactions.LinkedEntitiesService.create", return_value=transfer),
            patch("papita_txnsmodel.services.transactions.refresh_balance_materialized_views") as mock_refresh,
        ):
            service.create(obj=transfer, owner=owner)
        mock_refresh.assert_called_once()


class TestReportService:
    """ReportService implements FR-12 transaction analytics."""

    def test_spending_excludes_transfers(self, owner: UsersDTO):
        """Spending totals ignore TRANSFER rows."""
        service = ReportService()
        service.transactions_service = MagicMock()
        service.transactions_service.get_records.return_value = pd.DataFrame(
            [
                {
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 40.0,
                    "category_id": uuid.uuid4(),
                    "transaction_ts": datetime.now(timezone.utc),
                },
                {
                    "transaction_kind": TransactionKind.TRANSFER.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 100.0,
                    "category_id": None,
                    "transaction_ts": datetime.now(timezone.utc),
                },
                {
                    "transaction_kind": TransactionKind.INCOME.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 80.0,
                    "category_id": uuid.uuid4(),
                    "transaction_ts": datetime.now(timezone.utc),
                },
            ]
        )
        result = service.spending(owner=owner)
        assert result["expense_total"] == 40.0
        assert result["income_total"] == 80.0

    def test_export_returns_csv_stub(self, owner: UsersDTO):
        """Export delegates to spending and returns CSV text."""
        service = ReportService()
        with patch.object(ReportService, "spending", return_value={"expense_total": 1.0, "income_total": 2.0, "expenses": [], "group_by": "category"}):
            payload = service.export(owner=owner, report_type="spending", export_format="csv")
        assert isinstance(payload, str)
        assert "expense_total" in payload


class TestCategoriesGlobalWriteGuard:
    """Tenants cannot mutate global category seeds."""

    def test_create_global_category_rejected_for_tenant(self, owner: UsersDTO):
        """owner_id=None writes are blocked when owner context is present."""
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
            service._repository = MagicMock()
        category = CategoriesDTO(
            name="Global Rent",
            description="seed",
            category_kind=CategoryKind.EXPENSE,
            owner_id=None,
        )
        with pytest.raises(ValueError, match="global categories"):
            service.create(obj=category, owner=owner)
