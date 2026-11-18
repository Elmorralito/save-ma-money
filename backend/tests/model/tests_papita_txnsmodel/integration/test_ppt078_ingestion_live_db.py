"""B0 live-DB tests for PPT-078 provenance sidecar + ingestion bridge."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import text

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, IngestionSource, LedgerSide, TransactionKind
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.ingestion import IngestTransactionRequest, IngestionBridgeService
from papita_txnsmodel.services.transactions import TransactionsService

from .conftest import requires_postgres

_VALID_PASSWORD = "Password1!"


def _user(user_id: uuid.UUID, label: str) -> UsersDTO:
    return UsersDTO(
        id=user_id,
        username=f"ppt078_{label}",
        email=f"ppt078_{label}@example.local",
        password=_VALID_PASSWORD,
        auth_provider="local",
    )


def _cleanup(engine, *, account_id: uuid.UUID, category_id: uuid.UUID, txn_id: uuid.UUID | None) -> None:
    with engine.connect() as conn:
        if txn_id is not None:
            conn.execute(
                text("DELETE FROM papita_transactions.transaction_ingestion_provenance WHERE transaction_id = :id"),
                {"id": str(txn_id)},
            )
            conn.execute(
                text("DELETE FROM papita_transactions.transactions WHERE id = :id"),
                {"id": str(txn_id)},
            )
        conn.execute(
            text("DELETE FROM papita_transactions.accounts WHERE id = :id"),
            {"id": str(account_id)},
        )
        conn.execute(
            text("DELETE FROM papita_transactions.categories WHERE id = :id"),
            {"id": str(category_id)},
        )
        conn.commit()


@requires_postgres
class TestLiveDbPpt078IngestionBridge:
    """Idempotent ingest + soft-delete reactivate against Docker Postgres (B0)."""

    def test_idempotent_reingest_and_reactivate(
        self, postgres_connector, ensure_integration_users, integration_owner_ids
    ):
        """Same source_ref updates in place; soft-deleted rows reactivate."""
        owner = _user(integration_owner_ids["user_a"], "user_a")
        accounts = AccountsService()
        categories = CategoriesService()
        bridge = IngestionBridgeService()
        txns = TransactionsService()

        account, _ = accounts.create_account(
            obj=AccountsDTO(
                name=f"PPT078 cash {uuid.uuid4().hex[:8]}",
                description="ingest test",
                owner_id=owner.id,
                account_kind=AccountKind.OTHER_ASSET,
                ledger_side=LedgerSide.ASSET,
            ),
            owner=owner,
        )
        category = categories.create(
            obj=CategoriesDTO(
                name=f"PPT078 groceries {uuid.uuid4().hex[:8]}",
                description="ingest test",
                category_kind=CategoryKind.EXPENSE,
                owner_id=owner.id,
            ),
            owner=owner,
        )
        assert account.id is not None
        assert category.id is not None

        source_ref = f"csv:ppt078:{uuid.uuid4().hex}"
        ts = datetime(2026, 8, 11, 15, 30, 0)
        txn_id: uuid.UUID | None = None

        try:
            first = bridge.ingest_transaction(
                owner=owner,
                request=IngestTransactionRequest(
                    ingestion_source=IngestionSource.CSV,
                    source_ref=source_ref,
                    transaction_kind=TransactionKind.EXPENSE,
                    amount=11.25,
                    from_account_id=account.id,
                    category_id=category.id,
                    transaction_ts=ts,
                    description="first",
                ),
            )
            assert first.outcome == "created"
            assert first.provenance is not None
            txn_id = first.transaction.id
            assert txn_id is not None
            assert first.transaction.transaction_ts == ts

            second = bridge.ingest_transaction(
                owner=owner,
                request=IngestTransactionRequest(
                    ingestion_source=IngestionSource.CSV,
                    source_ref=source_ref,
                    transaction_kind=TransactionKind.EXPENSE,
                    amount=14.0,
                    from_account_id=account.id,
                    category_id=category.id,
                    description="updated",
                ),
            )
            assert second.outcome == "updated"
            assert second.transaction.id == txn_id
            assert second.transaction.transaction_ts == ts
            assert second.transaction.amount == 14.0
            assert second.provenance is not None
            assert second.provenance.id == first.provenance.id

            txns.delete(obj=second.transaction, owner=owner, hard=False)
            revived = bridge.ingest_transaction(
                owner=owner,
                request=IngestTransactionRequest(
                    ingestion_source=IngestionSource.CSV,
                    source_ref=source_ref,
                    transaction_kind=TransactionKind.EXPENSE,
                    amount=16.5,
                    from_account_id=account.id,
                    category_id=category.id,
                    description="revived",
                ),
            )
            assert revived.outcome == "reactivated"
            assert revived.transaction.id == txn_id
            assert revived.transaction.active is True
            assert revived.transaction.deleted_at is None
            assert revived.transaction.amount == 16.5
        finally:
            _cleanup(
                postgres_connector.engine,
                account_id=account.id,
                category_id=category.id,
                txn_id=txn_id,
            )

    def test_provenance_unique_index_exists(
        self, postgres_connector, ensure_integration_users, integration_owner_ids
    ):
        """Migration created the partial unique index on the sidecar."""
        with postgres_connector.engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'papita_transactions'
                      AND indexname = 'uq_txn_ingest_prov_owner_source_ref'
                    """
                )
            ).first()
        assert row is not None
