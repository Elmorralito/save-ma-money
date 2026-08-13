"""Unit tests for ingestion connection/run status services (PPT-083 / #177)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.ingestion_status import (
    IngestionConnectionService,
    IngestionRunService,
    RecordIngestionRunRequest,
    UpsertIngestionConnectionRequest,
)
from papita_txnsmodel.access.users.dto import UsersDTO


def _owner() -> UsersDTO:
    return UsersDTO(
        id=uuid.uuid4(),
        username="ingest_owner",
        email="ingest_owner@example.local",
        password="Password1!",
        auth_provider="local",
    )


def test_upsert_connection_reactivates_soft_deleted_natural_key() -> None:
    """Soft-deleted natural key must reuse id + reactivate (unique index not partial)."""
    owner = _owner()
    existing_id = uuid.uuid4()
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    soft_deleted = IngestionConnectionDTO(
        id=existing_id,
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        deployment_name="old-deploy",
        enabled=False,
        lookback_hours=12,
        active=False,
        deleted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        created_at=created_at,
        updated_at=created_at,
    )
    revived = soft_deleted.model_copy(
        update={
            "active": True,
            "deleted_at": None,
            "enabled": True,
            "lookback_hours": 24,
            "deployment_name": "papita-email-ingestion-hourly",
        }
    )

    service = IngestionConnectionService()
    repo = MagicMock()
    repo.get_by_natural_key.return_value = soft_deleted
    repo.upsert_record.return_value = revived
    service._connection_repository = repo  # noqa: SLF001
    service._repository = repo  # noqa: SLF001

    result = service.upsert_connection(
        owner=owner,
        request=UpsertIngestionConnectionRequest(
            provider="email",
            flow_name="papita-email-ingestion",
            deployment_name="papita-email-ingestion-hourly",
            enabled=True,
            lookback_hours=24,
        ),
    )

    assert result.id == existing_id
    assert result.active is True
    repo.get_by_natural_key.assert_called_once()
    assert repo.get_by_natural_key.call_args.kwargs["include_deleted"] is True
    upsert_kwargs = repo.upsert_record.call_args.kwargs
    assert upsert_kwargs["reactivate"] is True
    upserted_dto = repo.upsert_record.call_args.args[0]
    assert upserted_dto.id == existing_id
    assert upserted_dto.active is True
    assert upserted_dto.deleted_at is None


def test_upsert_connection_raises_when_repository_returns_none() -> None:
    owner = _owner()
    service = IngestionConnectionService()
    repo = MagicMock()
    repo.get_by_natural_key.return_value = None
    repo.upsert_record.return_value = None
    service._connection_repository = repo  # noqa: SLF001

    with pytest.raises(RuntimeError, match="Failed to upsert ingestion connection"):
        service.upsert_connection(
            owner=owner,
            request=UpsertIngestionConnectionRequest(
                provider="email",
                flow_name="papita-email-ingestion",
            ),
        )


def test_finish_run_raises_when_repository_returns_none() -> None:
    owner = _owner()
    run_id = uuid.uuid4()
    started = datetime.now(timezone.utc)
    existing = IngestionRunDTO(
        id=run_id,
        owner_id=owner.id,
        status=IngestionRunStatus.STARTED,
        started_at=started,
        created_at=started,
    )
    service = IngestionRunService()
    repo = MagicMock()
    service._run_repository = repo  # noqa: SLF001
    service._repository = repo  # noqa: SLF001

    with patch.object(service, "get", return_value=existing):
        repo.upsert_record.return_value = None
        with pytest.raises(RuntimeError, match="Failed to finish ingestion run"):
            service.finish_run(
                owner=owner,
                run_id=run_id,
                request=RecordIngestionRunRequest(
                    status=IngestionRunStatus.SUCCEEDED,
                    started_at=started,
                    finished_at=started,
                    fetched=1,
                    created=1,
                ),
            )
