"""Tests for API service dependency factories (PR-E / E6)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from papita_txnsapi.dependencies.services import (
    clear_transactions_service_cache,
    get_transactions_service,
)
from papita_txnsmodel.database.connector import SQLDatabaseConnector


class TestTransactionsServiceDiCache:
    """Module-scoped TransactionsService avoids per-request FK rewiring."""

    def setup_method(self) -> None:
        clear_transactions_service_cache()

    def teardown_method(self) -> None:
        clear_transactions_service_cache()

    def test_get_transactions_service_reuses_instance_per_connector(self) -> None:
        connector = SQLDatabaseConnector
        with (
            patch("papita_txnsapi.dependencies.services.AccountsService") as mock_accounts_cls,
            patch("papita_txnsapi.dependencies.services.CategoriesService") as mock_categories_cls,
            patch("papita_txnsapi.dependencies.services.TransactionTemplatesService") as mock_templates_cls,
            patch("papita_txnsapi.dependencies.services.TransactionsService") as mock_txn_cls,
        ):
            accounts = MagicMock(name="accounts")
            categories = MagicMock(name="categories")
            templates = MagicMock(name="templates")
            service = MagicMock(name="transactions")
            service.load_link_services.return_value = service
            mock_accounts_cls.model_validate.return_value = accounts
            mock_categories_cls.model_validate.return_value = categories
            mock_templates_cls.model_validate.return_value = templates
            mock_txn_cls.model_validate.return_value = service

            first = get_transactions_service(connector)
            second = get_transactions_service(connector)

            assert first is second
            assert first is service
            mock_txn_cls.model_validate.assert_called_once()
            service.load_link_services.assert_called_once_with(
                {
                    "template_id": templates,
                    "from_account_id": accounts,
                    "to_account_id": accounts,
                    "category_id": categories,
                }
            )
