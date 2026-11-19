"""Unit tests for PPT-078 ingestion bridge (provenance + kind validation)."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from papita_txnsmodel.access.ingestion.dto import TransactionIngestionProvenanceDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind
from papita_txnsmodel.services.ingestion import IngestTransactionRequest, IngestionBridgeService


def _owner() -> UsersDTO:
    return UsersDTO(
        id=uuid.uuid4(),
        username="ingest_owner",
        email="ingest_owner@example.local",
        password="Password1!",
        auth_provider="local",
    )


class TestIngestTransactionRequest:
    """Kind / account shape validation for the model-local ingest DTO."""

    def test_expense_requires_from_account_and_category(self):
        with pytest.raises(ValueError, match="EXPENSE"):
            IngestTransactionRequest(
                ingestion_source=IngestionSource.CSV,
                source_ref="row-1",
                transaction_kind=TransactionKind.EXPENSE,
                amount=10.0,
                to_account_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
            )

    def test_income_ok(self):
        req = IngestTransactionRequest(
            ingestion_source=IngestionSource.EMAIL,
            source_ref="msg-1",
            transaction_kind=TransactionKind.INCOME,
            amount=25.0,
            to_account_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
        )
        assert req.transaction_kind == TransactionKind.INCOME


class TestIngestionBridgeService:
    """Bridge create / re-ingest / reactivate paths with mocked repositories."""

    def test_create_new_with_provenance(self):
        owner = _owner()
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        txn_id = uuid.uuid4()
        ts = datetime(2026, 8, 1, 12, 0, 0)

        txn_service = MagicMock()
        created = TransactionsDTO(
            id=txn_id,
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=12.0,
            from_account_id=account_id,
            category_id=category_id,
            transaction_ts=ts,
        )
        txn_service.create.return_value = created

        prov_repo = MagicMock()
        prov_repo.get_by_source_ref.return_value = None
        prov_dto = TransactionIngestionProvenanceDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_id=txn_id,
            transaction_ts=ts,
            ingestion_source=IngestionSource.CSV,
            source_ref="csv:1",
        )
        prov_repo.upsert_record.return_value = prov_dto

        service = IngestionBridgeService(transactions_service=txn_service)
        service._repository = prov_repo

        result = service.ingest_transaction(
            owner=owner,
            request=IngestTransactionRequest(
                ingestion_source=IngestionSource.CSV,
                source_ref="csv:1",
                transaction_kind=TransactionKind.EXPENSE,
                amount=12.0,
                from_account_id=account_id,
                category_id=category_id,
                transaction_ts=ts,
            ),
        )

        assert result.outcome == "created"
        assert result.transaction.id == txn_id
        assert result.provenance is not None
        assert result.provenance.source_ref == "csv:1"
        txn_service.create.assert_called_once()
        prov_repo.upsert_record.assert_called_once()

    def test_reingest_updates_and_keeps_id(self):
        owner = _owner()
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        txn_id = uuid.uuid4()
        ts = datetime(2026, 8, 2, 9, 0, 0)
        prov_id = uuid.uuid4()

        existing_prov = TransactionIngestionProvenanceDTO(
            id=prov_id,
            owner_id=owner.id,
            transaction_id=txn_id,
            transaction_ts=ts,
            ingestion_source=IngestionSource.CSV,
            source_ref="csv:99",
            active=True,
        )
        existing_txn = TransactionsDTO(
            id=txn_id,
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=5.0,
            from_account_id=account_id,
            category_id=category_id,
            transaction_ts=ts,
            active=True,
        )
        updated_txn = existing_txn.model_copy(update={"amount": 7.5})

        txn_service = MagicMock()
        txn_service.create.return_value = updated_txn

        prov_repo = MagicMock()
        prov_repo.get_by_source_ref.return_value = existing_prov
        prov_repo.upsert_record.return_value = existing_prov

        txn_repo = MagicMock()
        txn_repo.get_record_by_id.return_value = existing_txn

        service = IngestionBridgeService(transactions_service=txn_service)
        service._repository = prov_repo

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "papita_txnsmodel.services.ingestion.TransactionsRepository",
                lambda: txn_repo,
            )
            result = service.ingest_transaction(
                owner=owner,
                request={
                    "ingestion_source": "CSV",
                    "source_ref": "csv:99",
                    "transaction_kind": "EXPENSE",
                    "amount": 7.5,
                    "from_account_id": account_id,
                    "category_id": category_id,
                },
            )

        assert result.outcome == "updated"
        assert result.transaction.id == txn_id
        create_kwargs = txn_service.create.call_args.kwargs
        assert create_kwargs["reactivate"] is True
        assert create_kwargs["obj"].id == txn_id
        assert create_kwargs["obj"].transaction_ts == ts

    def test_reingest_reactivates_soft_deleted(self):
        owner = _owner()
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        txn_id = uuid.uuid4()
        ts = datetime(2026, 8, 3, 9, 0, 0)

        existing_prov = TransactionIngestionProvenanceDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_id=txn_id,
            transaction_ts=ts,
            ingestion_source=IngestionSource.API,
            source_ref="api:1",
            active=False,
            deleted_at=datetime(2026, 8, 4),
        )
        existing_txn = TransactionsDTO(
            id=txn_id,
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=5.0,
            from_account_id=account_id,
            category_id=category_id,
            transaction_ts=ts,
            active=False,
            deleted_at=datetime(2026, 8, 4),
        )
        revived = existing_txn.model_copy(update={"active": True, "deleted_at": None, "amount": 9.0})

        txn_service = MagicMock()
        txn_service.create.return_value = revived
        prov_repo = MagicMock()
        prov_repo.get_by_source_ref.return_value = existing_prov
        prov_repo.upsert_record.return_value = existing_prov.model_copy(update={"active": True, "deleted_at": None})
        txn_repo = MagicMock()
        txn_repo.get_record_by_id.return_value = existing_txn

        service = IngestionBridgeService(transactions_service=txn_service)
        service._repository = prov_repo

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "papita_txnsmodel.services.ingestion.TransactionsRepository",
                lambda: txn_repo,
            )
            result = service.ingest_transaction(
                owner=owner,
                request=IngestTransactionRequest(
                    ingestion_source=IngestionSource.API,
                    source_ref="api:1",
                    transaction_kind=TransactionKind.EXPENSE,
                    amount=9.0,
                    from_account_id=account_id,
                    category_id=category_id,
                ),
            )

        assert result.outcome == "reactivated"

    def test_record_dead_letter(self):
        owner = _owner()
        dlq_repo = MagicMock()
        dlq_repo.upsert_record.side_effect = lambda dto, **kwargs: dto
        service = IngestionBridgeService(transactions_service=MagicMock())
        service._dead_letter_repository = dlq_repo

        row = service.record_dead_letter(
            owner=owner,
            ingestion_source=IngestionSource.EMAIL,
            raw_payload='{"bad": true}',
            error_message="parse failed",
            source_ref="msg-x",
        )
        assert row.error_message == "parse failed"
        assert row.source_ref == "msg-x"
        dlq_repo.upsert_record.assert_called_once()
