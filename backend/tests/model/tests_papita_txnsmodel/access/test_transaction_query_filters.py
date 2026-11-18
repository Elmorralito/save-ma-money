"""Tests for transaction list SQLModel filter builders."""

from __future__ import annotations

import uuid

from papita_txnsmodel.access.transactions.query_filters import TransactionListFilterSpec, build_transaction_list_filters
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions


class TestTransactionQueryFilters:
    """Verify ORM filter expressions target expected columns."""

    def test_excludes_transfer_by_default(self) -> None:
        filters = build_transaction_list_filters(TransactionListFilterSpec(exclude_transfer=True))
        assert len(filters) == 1
        assert str(filters[0]).startswith(str(Transactions.transaction_kind != TransactionKind.TRANSFER))

    def test_transfer_kind_filter(self) -> None:
        filters = build_transaction_list_filters(
            TransactionListFilterSpec(transaction_kind=TransactionKind.TRANSFER)
        )
        assert len(filters) == 1
        assert str(filters[0]).startswith(str(Transactions.transaction_kind == TransactionKind.TRANSFER))

    def test_account_id_matches_either_leg(self) -> None:
        account_id = uuid.uuid4()
        filters = build_transaction_list_filters(TransactionListFilterSpec(account_id=account_id))
        assert len(filters) == 1

    def test_status_filter(self) -> None:
        filters = build_transaction_list_filters(TransactionListFilterSpec(status=TransactionStatus.PENDING))
        assert len(filters) == 1
        assert str(filters[0]).startswith(str(Transactions.status == TransactionStatus.PENDING))
