"""Unit tests for ingestion connection/run status services (PPT-083 / #177)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.ingestion_status import (
    IngestionConnectionService,
    IngestionRunService,
    RecordIngestionRunRequest,
    UpdateIngestionConnectionRequest,
    UpsertIngestionConnectionRequest,
)


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


def test_upsert_connection_preserves_existing_user_config_when_requested() -> None:
    """Worker status upserts must not overwrite user-configured DB filters."""
    owner = _owner()
    existing_id = uuid.uuid4()
    existing = IngestionConnectionDTO(
        id=existing_id,
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        deployment_name="papita-email-ingestion-hourly",
        enabled=False,
        lookback_hours=6,
        email_senders=["chase.com", "global66.com"],
        email_subjects=["Transaction Alert"],
        email_source_label="Finanzas",
        email_query="in:inbox",
    )

    service = IngestionConnectionService()
    repo = MagicMock()
    repo.get_by_natural_key.return_value = existing
    repo.upsert_record.side_effect = lambda dto, **_kw: dto
    service._connection_repository = repo  # noqa: SLF001

    result = service.upsert_connection(
        owner=owner,
        request=UpsertIngestionConnectionRequest(
            provider="email",
            flow_name="papita-email-ingestion",
            enabled=True,
            lookback_hours=24,
            email_senders=["notificacionesbancolombia.com"],
        ),
        preserve_existing_config=True,
    )

    assert result.id == existing_id
    assert result.enabled is False
    assert result.lookback_hours == 6
    assert result.email_senders == ["chase.com", "global66.com"]
    assert result.email_subjects == ["Transaction Alert"]
    assert result.email_source_label == "Finanzas"
    assert result.email_query == "in:inbox"


def test_update_connection_applies_partial_updates_and_normalizes_terms() -> None:
    owner = _owner()
    conn_id = uuid.uuid4()
    existing = IngestionConnectionDTO(
        id=conn_id,
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        enabled=True,
        lookback_hours=24,
        email_senders=["notificacionesbancolombia.com"],
    )

    service = IngestionConnectionService()
    repo = MagicMock()
    repo.upsert_record.side_effect = lambda dto, **_kw: dto
    service._connection_repository = repo  # noqa: SLF001
    service._repository = repo  # noqa: SLF001

    with patch.object(service, "get", return_value=existing):
        updated = service.update_connection(
            owner=owner,
            connection_id=conn_id,
            request=UpdateIngestionConnectionRequest(
                email_senders=[" nequi.com.co ", "nequi.com.co", ""],
                email_source_label="  ",
                lookback_hours=12,
            ),
        )

    assert updated is not None
    assert updated.email_senders == ["nequi.com.co"]
    assert updated.email_source_label is None
    assert updated.lookback_hours == 12
    assert updated.enabled is True

    with patch.object(service, "get", return_value=None):
        assert (
            service.update_connection(
                owner=owner,
                connection_id=uuid.uuid4(),
                request=UpdateIngestionConnectionRequest(enabled=False),
            )
            is None
        )


def test_delete_connection_disables_and_soft_deletes() -> None:
    owner = _owner()
    conn_id = uuid.uuid4()
    existing = IngestionConnectionDTO(
        id=conn_id,
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        enabled=True,
        lookback_hours=24,
    )
    service = IngestionConnectionService()
    repo = MagicMock()
    service._connection_repository = repo  # noqa: SLF001
    service._repository = repo  # noqa: SLF001

    with patch.object(service, "get", return_value=existing), patch.object(service, "delete") as mock_delete:
        assert service.delete_connection(owner=owner, connection_id=conn_id) is True
        saved_dto = repo.upsert_record.call_args.args[0]
        assert saved_dto.enabled is False
        mock_delete.assert_called_once_with(obj=saved_dto, owner=owner, hard=False)

    with patch.object(service, "get", return_value=None):
        assert service.delete_connection(owner=owner, connection_id=uuid.uuid4()) is False
