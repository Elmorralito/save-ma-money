"""v3 handler and service wiring tests."""

import uuid
import warnings
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.handlers.account_extensions import (
    AccountFinancingTableHandler,
    BankingAccountDetailsTableHandler,
)
from papita_txnsmodel.handlers.accounts import AccountsTableHandler
from papita_txnsmodel.handlers.categories import CategoriesTableHandler
from papita_txnsmodel.handlers.factory import HandlerFactory
from papita_txnsmodel.handlers.matching import ReferenceIndex, bulk_match_column
from papita_txnsmodel.handlers.transactions import TransactionTemplatesTableHandler, TransactionsHandler
from papita_txnsmodel.handlers.users import UsersTableHandler
from papita_txnsmodel.model.enums import TransactionKind
from papita_txnsmodel.services.account_details import BankingAccountDetailsService
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.extends import LinkedEntity
from papita_txnsmodel.services.transactions import TransactionTemplatesService, TransactionsService
from papita_txnsmodel.services.users import UsersService

_VALID_PASSWORD = "Password1!"


def _user() -> UsersDTO:
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
        return service


def _categories_service() -> CategoriesService:
    with patch("papita_txnsmodel.services.categories.CategoriesRepository"):
        service = CategoriesService()
        service._repository = MagicMock()
        return service


def _templates_service() -> TransactionTemplatesService:
    with (
        patch("papita_txnsmodel.services.transactions.TransactionTemplatesRepository"),
        patch("papita_txnsmodel.services.categories.CategoriesRepository"),
    ):
        service = TransactionTemplatesService()
        service._repository = MagicMock()
        service.categories_service = _categories_service()
        return service


def _transactions_service() -> TransactionsService:
    with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
        service = TransactionsService()
        service._repository = MagicMock()
        return service


class TestHandlerInstantiation:
    """Handlers should construct with v3 dependency wiring."""

    def test_accounts_table_handler_instantiates(self):
        """Accounts handler accepts principal service without extra dependencies."""
        handler = AccountsTableHandler(service=_accounts_service())
        assert handler.labels() == ("accounts", "accounts_table", "account_table", "general_accounts")

    def test_categories_table_handler_instantiates(self):
        """Categories handler wires parent_id dependency."""
        handler = CategoriesTableHandler(service=_categories_service())
        assert "categories" in handler.labels()
        assert "parent_id" in handler.dependencies
        assert isinstance(handler.dependencies["parent_id"], CategoriesService)

    def test_categories_legacy_labels_warn(self):
        """Legacy types labels resolve with DeprecationWarning."""
        HandlerFactory.registry.clear_handlers()
        HandlerFactory.load("papita_txnsmodel.handlers.categories")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            handler_cls = HandlerFactory.get(("types",))
        assert handler_cls is CategoriesTableHandler
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    def test_transaction_templates_handler_wires_category_id(self):
        """Templates handler resolves categories through category_id dependency."""
        handler = TransactionTemplatesTableHandler(service=_templates_service())
        assert "category_id" in handler.dependencies
        assert isinstance(handler.dependencies["category_id"], CategoriesService)

    def test_transactions_handler_instantiates(self):
        """Transactions handler wires account and template services."""
        handler = TransactionsHandler(
            service=_transactions_service(),
            accounts_service=_accounts_service(),
            transaction_templates_service=_templates_service(),
        )
        assert handler.labels() == ("transactions_handler", "transactions")

    def test_banking_account_details_handler_wires_account_id(self):
        """Banking details handler resolves account_id through AccountsService."""
        with patch("papita_txnsmodel.services.account_details.BankingAccountDetailsRepository"):
            service = BankingAccountDetailsService()
            service._repository = MagicMock()
        handler = BankingAccountDetailsTableHandler(service=service)
        assert "account_id" in handler.dependencies
        assert isinstance(handler.dependencies["account_id"], AccountsService)

    def test_account_financing_handler_wires_accounts(self):
        """Financing handler resolves asset and loan account references."""
        with patch("papita_txnsmodel.services.account_financing.AccountFinancingRepository"):
            service = AccountFinancingService()
            service._repository = MagicMock()
        handler = AccountFinancingTableHandler(service=service)
        assert "asset_account_id" in handler.dependencies
        assert "loan_account_id" in handler.dependencies


class TestHandlerFactoryDiscovery:
    """HandlerFactory should register all v3 handlers from the handlers package."""

    def test_factory_registers_users_and_extension_handlers(self):
        """Loading papita_txnsmodel.handlers registers users and detail handlers."""
        HandlerFactory.registry.clear_handlers()
        HandlerFactory.load("papita_txnsmodel.handlers")
        assert HandlerFactory.get(("users",)) is UsersTableHandler
        assert HandlerFactory.get(("banking_account_details",)) is BankingAccountDetailsTableHandler
        assert HandlerFactory.get(("account_financing",)) is AccountFinancingTableHandler


class TestUsersTableHandler:
    """Users handler supports tenant-root ingest."""

    def test_users_table_handler_instantiates(self):
        """Users handler accepts principal service without extra dependencies."""
        with patch("papita_txnsmodel.services.users.UsersRepository"):
            service = UsersService()
            service._repository = MagicMock()
        handler = UsersTableHandler(service=service)
        assert handler.labels() == ("users", "users_table", "user_table")


class TestBulkReferenceMatching:
    """Bulk matching should resolve names without per-row apply."""

    def test_reference_index_resolves_name(self):
        """Name lookup returns the matching record id."""
        account_id = uuid.uuid4()
        core = pd.DataFrame([{"id": account_id, "name": "cash", "tags": []}])
        index = ReferenceIndex(core, id_column="id", name_column="name", tags_column="tags")
        assert index.resolve_exact("cash") == account_id

    def test_bulk_match_column_maps_series(self):
        """Series values are mapped in bulk via the reference index."""
        account_id = uuid.uuid4()
        core = pd.DataFrame([{"id": account_id, "name": "cash", "tags": []}])
        index = ReferenceIndex(core, id_column="id", name_column="name", tags_column="tags")
        series = pd.Series(["cash", None])
        matched = bulk_match_column(series, index)
        assert matched.iloc[0] == account_id
        assert pd.isna(matched.iloc[1])


class TestTransactionsHandlerMatching:
    """Account matching must preserve v3 TRANSFER rows."""

    def test_match_accounts_keeps_transfer_rows(self):
        """Rows with both from and to account ids are retained for TRANSFER semantics."""
        handler = TransactionsHandler(
            service=_transactions_service(),
            accounts_service=_accounts_service(),
        )
        account_id = uuid.uuid4()
        handler.accounts_service.get_records = MagicMock(
            return_value=pd.DataFrame([{"id": account_id, "name": "cash", "tags": []}])
        )
        data = pd.DataFrame(
            [
                {
                    "from_account_id": account_id,
                    "to_account_id": account_id,
                    "transaction_kind": TransactionKind.TRANSFER.value,
                }
            ]
        )
        matched = handler._match_accounts(data)
        assert len(matched.index) == 1

    def test_match_categories_resolves_name(self):
        """Category names in ingest data resolve to category ids."""
        handler = TransactionsHandler(
            service=_transactions_service(),
            accounts_service=_accounts_service(),
            categories_service=_categories_service(),
        )
        category_id = uuid.uuid4()
        account_id = uuid.uuid4()
        handler.accounts_service.get_records = MagicMock(
            return_value=pd.DataFrame([{"id": account_id, "name": "cash", "tags": []}])
        )
        handler.categories_service.get_records = MagicMock(
            return_value=pd.DataFrame([{"id": category_id, "name": "groceries", "tags": []}])
        )
        data = pd.DataFrame(
            [
                {
                    "from_account_id": "cash",
                    "category_id": "groceries",
                    "transaction_kind": TransactionKind.EXPENSE.value,
                    "amount": 10.0,
                }
            ]
        )
        matched = handler._match_categories(handler._match_accounts(data))
        assert matched.iloc[0]["category_id"] == category_id


class TestOwnedServiceOwnerGuard:
    """OwnedTableDTO services must receive owner=UsersDTO."""

    def test_accounts_service_requires_owner_on_get_records(self):
        """get_records without owner raises for owned tables."""
        service = _accounts_service()
        with pytest.raises(ValueError, match="requires owner=UsersDTO"):
            service.get_records(dto=None)


class TestTransactionsDtoMapping:
    """Transactions DTO must round-trip ORM column names."""

    def test_to_dao_uses_account_id_columns(self):
        """to_dao emits from_account_id and to_account_id for SQLModel validation."""
        account_id = uuid.uuid4()
        dto = TransactionsDTO(
            owner_id=uuid.uuid4(),
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            from_account_id=account_id,
        )
        dao = dto.to_dao()
        assert dao.from_account_id == account_id
        assert dao.to_account_id is None


class TestLinkedEntityLoader:
    """LinkedEntity must assign service on first load."""

    def test_load_other_entity_service_assigns_on_first_call(self):
        """First load_other_entity_service call stores the linked service."""
        link = LinkedEntity(expected_other_entity_service_type=AccountsService)
        service = _accounts_service()
        link.load_other_entity_service(service)
        assert link.other_entity_service is service
