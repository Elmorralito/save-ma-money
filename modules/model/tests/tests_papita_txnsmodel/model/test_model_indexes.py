"""Tests for SQLModel table index definitions."""

from papita_txnsmodel.model.account_financing import AccountFinancing
from papita_txnsmodel.model.accounts import Accounts
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.transactions import TransactionTemplates, Transactions


class TestModelTableIndexes:
    """Owned-table and ledger models expose expected indexes."""

    def test_accounts_has_owner_active_index(self):
        """Active account listings per tenant use owner_id + active."""
        index_names = {index.name for index in Accounts.__table__.indexes}
        assert "ix_accounts_owner_active" in index_names

    def test_transactions_has_ledger_indexes(self):
        """Ledger joins and MV refresh filter on owner, status, and account FKs."""
        index_names = {index.name for index in Transactions.__table__.indexes}
        assert "ix_transactions_owner_active_status" in index_names
        assert "ix_transactions_from_account_id" in index_names
        assert "ix_transactions_to_account_id" in index_names
        assert "ix_transactions_owner_transaction_ts" in index_names
        assert "ix_transactions_category_id" in index_names
        assert "ix_transactions_id" in index_names

    def test_transaction_templates_has_owner_category_index(self):
        """Templates are commonly listed per owner and category."""
        index_names = {index.name for index in TransactionTemplates.__table__.indexes}
        assert "ix_transaction_templates_owner_category" in index_names

    def test_transaction_templates_has_owner_due_date_index(self):
        """One-off payment dues are listed per owner and due_date (PPT-071)."""
        index_names = {index.name for index in TransactionTemplates.__table__.indexes}
        assert "ix_transaction_templates_owner_due_date" in index_names

    def test_categories_has_unique_owner_name_kind_index(self):
        """FR-15 uniqueness constraint remains on the model."""
        index_names = {index.name for index in Categories.__table__.indexes}
        assert "uq_categories_owner_name_kind" in index_names

    def test_account_financing_has_loan_account_lookup_index(self):
        """Financing rows are queried by loan account id."""
        index_names = {index.name for index in AccountFinancing.__table__.indexes}
        assert "ix_account_financing_loan_account_id" in index_names
