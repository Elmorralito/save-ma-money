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
        auth_provider="local",
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
        """list_transfers queries transaction_kind=TRANSFER with SQL pagination."""
        service = _transactions_service()
        service._repository.get_records.return_value = pd.DataFrame()
        service._repository.count_records.return_value = 0
        records, total = service.list_transfers(owner=owner, skip=10, limit=25)
        assert total == 0
        assert service._repository.count_records.call_count == 1
        assert service._repository.get_records.call_count == 1
        assert service._repository.get_records.call_args.kwargs["skip"] == 10
        assert service._repository.get_records.call_args.kwargs["limit"] == 25

    def test_list_transactions_applies_sql_pagination(self, owner: UsersDTO):
        """list_transactions passes skip/limit to the repository query."""
        service = _transactions_service()
        service._repository.get_records.return_value = pd.DataFrame()
        service._repository.count_records.return_value = 42
        records, total = service.list_transactions(owner=owner, skip=5, limit=15)
        assert total == 42
        assert service._repository.count_records.call_count == 1
        assert service._repository.get_records.call_args.kwargs["skip"] == 5
        assert service._repository.get_records.call_args.kwargs["limit"] == 15

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

    def test_create_skips_balance_refresh_by_default(self, owner: UsersDTO):
        """Single create does not refresh MVs unless refresh_balances=True."""
        service = _transactions_service()
        transfer = TransactionsDTO(owner_id=owner.id, transaction_kind=TransactionKind.EXPENSE, amount=5.0)
        with (
            patch("papita_txnsmodel.services.transactions.LinkedEntitiesService.create", return_value=transfer),
            patch("papita_txnsmodel.services.transactions.refresh_balance_materialized_views") as mock_refresh,
        ):
            service.create(obj=transfer, owner=owner)
        mock_refresh.assert_not_called()

    def test_create_refreshes_balances_when_enabled(self, owner: UsersDTO):
        """Opt-in refresh_balances=True still refreshes MVs after create."""
        service = _transactions_service()
        transfer = TransactionsDTO(owner_id=owner.id, transaction_kind=TransactionKind.EXPENSE, amount=5.0)
        with (
            patch("papita_txnsmodel.services.transactions.LinkedEntitiesService.create", return_value=transfer),
            patch("papita_txnsmodel.services.transactions.refresh_balance_materialized_views") as mock_refresh,
        ):
            service.create(obj=transfer, owner=owner, refresh_balances=True)
        mock_refresh.assert_called_once()


class TestReportService:
    """ReportService implements FR-12 transaction analytics."""

    def test_spending_excludes_transfers(self, owner: UsersDTO):
        """Spending totals ignore TRANSFER rows."""
        service = ReportService()
        service.transactions_service = MagicMock()
        service.accounts_service = MagicMock()
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
        service.transactions_service.get_records.assert_called_once()
        assert service.transactions_service.get_records.call_args.kwargs["owner"] is owner

    def test_spending_filters_by_account_id(self, owner: UsersDTO):
        """Optional account_id keeps matching legs only."""
        account_a = uuid.uuid4()
        account_b = uuid.uuid4()
        service = ReportService()
        service.transactions_service = MagicMock()
        service.accounts_service = MagicMock()
        service.accounts_service.get.return_value = MagicMock(id=account_a)
        service.transactions_service.get_records.return_value = pd.DataFrame(
            [
                {
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 40.0,
                    "category_id": uuid.uuid4(),
                    "from_account_id": account_a,
                    "to_account_id": None,
                    "transaction_ts": datetime.now(timezone.utc),
                },
                {
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 25.0,
                    "category_id": uuid.uuid4(),
                    "from_account_id": account_b,
                    "to_account_id": None,
                    "transaction_ts": datetime.now(timezone.utc),
                },
            ]
        )
        result = service.spending(owner=owner, account_id=account_a)
        assert result["expense_total"] == 40.0
        service.accounts_service.get.assert_called_once_with(obj=account_a, owner=owner)

    def test_spending_rejects_foreign_account_id(self, owner: UsersDTO):
        """account_id not owned by the tenant raises before aggregation."""
        service = ReportService()
        service.transactions_service = MagicMock()
        service.accounts_service = MagicMock()
        service.accounts_service.get.return_value = None
        with pytest.raises(ValueError, match="Account not found for tenant"):
            service.spending(owner=owner, account_id=uuid.uuid4())
        service.transactions_service.get_records.assert_not_called()

    def test_require_owner_rejects_missing_tenant(self):
        """Reports cannot run without a tenant owner id."""
        service = ReportService()
        service.transactions_service = MagicMock()
        service.accounts_service = MagicMock()
        with pytest.raises(ValueError, match="require owner"):
            service.spending(owner=UsersDTO.model_construct(id=None))

    def test_seeded_totals_match_fr12_rules(self, owner: UsersDTO):
        """AC: correct totals against seeded ledger rows (COMPLETED + kind rules)."""
        category_id = uuid.uuid4()
        account_id = uuid.uuid4()
        now = datetime(2026, 2, 15, tzinfo=timezone.utc)
        service = ReportService()
        service.transactions_service = MagicMock()
        service.accounts_service = MagicMock()
        service.accounts_service.get.return_value = MagicMock(id=account_id)
        service.account_balances_service = MagicMock()
        service.account_balances_service.get_balances.return_value = pd.DataFrame(
            [{"account_id": account_id, "balance": 900.0}]
        )
        service.transactions_service.get_records.return_value = pd.DataFrame(
            [
                {
                    "transaction_kind": TransactionKind.INCOME.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 500.0,
                    "category_id": category_id,
                    "from_account_id": None,
                    "to_account_id": account_id,
                    "transaction_ts": now,
                },
                {
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 120.0,
                    "category_id": category_id,
                    "from_account_id": account_id,
                    "to_account_id": None,
                    "transaction_ts": now,
                },
                {
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "status": TransactionStatus.PENDING.value,
                    "amount": 50.0,
                    "category_id": category_id,
                    "from_account_id": account_id,
                    "to_account_id": None,
                    "transaction_ts": now,
                },
                {
                    "transaction_kind": TransactionKind.TRANSFER.value,
                    "status": TransactionStatus.COMPLETED.value,
                    "amount": 75.0,
                    "category_id": None,
                    "from_account_id": account_id,
                    "to_account_id": uuid.uuid4(),
                    "transaction_ts": now,
                },
            ]
        )

        spending = service.spending(owner=owner)
        assert spending["expense_total"] == 120.0
        assert spending["income_total"] == 500.0

        with patch("papita_txnsmodel.services.reports.refresh_balance_materialized_views") as mock_refresh:
            cash_flow = service.cash_flow(owner=owner, account_id=account_id, refresh_balances=True)
        mock_refresh.assert_called_once()
        assert cash_flow["inflows"] == 575.0  # 500 income + 75 transfer
        assert cash_flow["outflows"] == 195.0  # 120 expense + 75 transfer
        assert cash_flow["net"] == 380.0
        assert cash_flow["portfolio_total"] == 900.0
        service.account_balances_service.get_balances.assert_called_once_with(owner=owner, account_id=account_id)

        trends = service.trends(owner=owner, period="monthly")
        assert trends["period"] == "monthly"
        assert len(trends["series"]) == 2
        by_kind = {row["transaction_kind"]: row["total"] for row in trends["series"]}
        assert by_kind[TransactionKind.INCOME.value] == 500.0
        assert by_kind[TransactionKind.EXPENSE.value] == 120.0

    def test_cash_flow_skips_balance_refresh_by_default(self, owner: UsersDTO):
        """cash_flow default avoids MV refresh on export/read paths."""
        service = ReportService()
        service.transactions_service = MagicMock()
        service.transactions_service.get_records.return_value = pd.DataFrame()
        service.account_balances_service = MagicMock()
        service.account_balances_service.get_balances.return_value = pd.DataFrame()
        with patch("papita_txnsmodel.services.reports.refresh_balance_materialized_views") as mock_refresh:
            service.cash_flow(owner=owner)
        mock_refresh.assert_not_called()

    def test_export_returns_csv_stub(self, owner: UsersDTO):
        """Export delegates to spending and returns CSV text."""
        service = ReportService()
        service.accounts_service = MagicMock()
        with patch.object(
            ReportService,
            "spending",
            return_value={"expense_total": 1.0, "income_total": 2.0, "expenses": [], "group_by": "category"},
        ):
            payload = service.export(owner=owner, report_type="spending", export_format="csv")
        assert isinstance(payload, str)
        assert "expense_total" in payload


class TestCategoriesGlobalWriteGuard:
    """Tenants cannot mutate global category seeds; service ops require owner=."""

    def test_tenant_create_with_unassigned_owner_id_succeeds(self, owner: UsersDTO):
        """New tenant categories omit owner_id; repository assigns it on upsert."""
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
            service._repository = MagicMock()
            service._repository.get_records.return_value = __import__("pandas").DataFrame()
            service._repository.upsert_record.return_value = CategoriesDTO(
                name="Rent",
                description="seed",
                category_kind=CategoryKind.EXPENSE,
                owner_id=owner.id,
            )
        category = CategoriesDTO(
            name="Rent",
            description="seed",
            category_kind=CategoryKind.EXPENSE,
            owner_id=None,
        )
        result = service.create(obj=category, owner=owner)
        assert result.name == "Rent"
        service._repository.upsert_record.assert_called_once()

    def test_requires_owner_on_get_records(self):
        """Omitting owner= raises so unscoped category lists cannot leak tenants."""
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
        with pytest.raises(ValueError, match="requires owner"):
            service.get_records(dto=None)

    def test_requires_owner_on_create(self):
        """Create without owner= is rejected before repository I/O."""
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
        with pytest.raises(ValueError, match="requires owner"):
            service.create(
                obj=CategoriesDTO(
                    name="Rent",
                    description="seed",
                    category_kind=CategoryKind.EXPENSE,
                )
            )

    def test_rejects_global_category_delete(self, owner: UsersDTO):
        """Soft-delete must not touch owner_id IS NULL seed rows."""
        global_id = uuid.uuid4()
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
            service._repository = MagicMock()
            service._repository.get_records.return_value = __import__("pandas").DataFrame(
                [{"id": global_id, "owner_id": None, "name": "Utilities"}]
            )
        with pytest.raises(ValueError, match="global categories"):
            service.delete(obj=CategoriesDTO.model_construct(id=global_id), owner=owner)
        service._repository.soft_delete_records.assert_not_called()
        service._repository.hard_delete_records.assert_not_called()

    def test_rejects_global_category_update_via_create(self, owner: UsersDTO):
        """Upsert/update path refuses existing global primary keys."""
        global_id = uuid.uuid4()
        with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
            service = CategoriesService()
            service._repository = MagicMock()
            service._repository.get_records.return_value = __import__("pandas").DataFrame(
                [{"id": global_id, "owner_id": None, "name": "Utilities"}]
            )
        with pytest.raises(ValueError, match="global categories"):
            service.create(
                obj=CategoriesDTO(
                    id=global_id,
                    name="Tampered",
                    description="seed",
                    category_kind=CategoryKind.EXPENSE,
                    owner_id=owner.id,
                ),
                owner=owner,
            )
        service._repository.upsert_record.assert_not_called()
