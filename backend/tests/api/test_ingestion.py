"""Ingestion connection/run-status router tests (PPT-083 / #177 T7–T8, T10)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionRunStatus


def _connection_dto(owner: UsersDTO, *, connection_id: uuid.UUID | None = None) -> IngestionConnectionDTO:
    now = datetime.now(timezone.utc)
    return IngestionConnectionDTO(
        id=connection_id or uuid.uuid4(),
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        deployment_name="papita-email-ingestion-hourly",
        enabled=True,
        lookback_hours=24,
        created_at=now,
        updated_at=now,
    )


def _run_dto(owner: UsersDTO, *, connection_id: uuid.UUID | None = None) -> IngestionRunDTO:
    started = datetime.now(timezone.utc)
    return IngestionRunDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        connection_id=connection_id,
        status=IngestionRunStatus.SUCCEEDED,
        started_at=started,
        finished_at=started,
        fetched=2,
        created=2,
        flow_name="papita-email-ingestion",
        deployment_name="papita-email-ingestion-hourly",
    )


def test_ingestion_routes_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/ingestion/connections").status_code == 401
    assert client.get("/api/v1/ingestion/runs").status_code == 401
    assert client.get("/api/v1/ingestion/runs/latest").status_code == 401


def test_list_connections_and_get_by_id(ingestion_client) -> None:
    test_client, owner, mock_connections, _mock_runs = ingestion_client
    conn = _connection_dto(owner)
    mock_connections.count_records.return_value = 1
    mock_connections.list_connections.return_value = [conn]
    mock_connections.get_connection.return_value = conn

    listed = test_client.get("/api/v1/ingestion/connections")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(conn.id)
    assert body["items"][0]["provider"] == "email"
    assert "raw_payload" not in body["items"][0]
    assert "refresh_token" not in body["items"][0]
    mock_connections.list_connections.assert_called_once()

    got = test_client.get(f"/api/v1/ingestion/connections/{conn.id}")
    assert got.status_code == 200
    assert got.json()["flow_name"] == "papita-email-ingestion"


def test_get_connection_cross_tenant_is_404(ingestion_client) -> None:
    test_client, _owner, mock_connections, _mock_runs = ingestion_client
    mock_connections.get_connection.return_value = None
    response = test_client.get(f"/api/v1/ingestion/connections/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingestion connection not found"


def test_list_runs_and_latest(ingestion_client) -> None:
    test_client, owner, _mock_connections, mock_runs = ingestion_client
    run = _run_dto(owner)
    mock_runs.count_records.return_value = 1
    mock_runs.list_runs.return_value = [run]
    mock_runs.get_latest_run.return_value = run

    listed = test_client.get("/api/v1/ingestion/runs?skip=0&limit=10")
    assert listed.status_code == 200
    body = listed.json()
    assert body["items"][0]["status"] == "succeeded"
    assert body["items"][0]["fetched"] == 2
    assert "failures" not in body["items"][0]
    assert "raw_payload" not in body["items"][0]

    latest = test_client.get("/api/v1/ingestion/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == str(run.id)


def test_latest_run_missing_is_404(ingestion_client) -> None:
    test_client, _owner, _mock_connections, mock_runs = ingestion_client
    mock_runs.get_latest_run.return_value = None
    response = test_client.get("/api/v1/ingestion/runs/latest")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingestion run not found"


def test_openapi_includes_ingestion_paths(client: TestClient) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = spec["paths"]
    assert "/api/v1/ingestion/connections" in paths
    assert "/api/v1/ingestion/connections/{connection_id}" in paths
    assert "/api/v1/ingestion/runs" in paths
    assert "/api/v1/ingestion/runs/latest" in paths
    # Read-only: no POST trigger route.
    assert "post" not in paths["/api/v1/ingestion/connections"]
    assert "post" not in paths.get("/api/v1/ingestion/runs", {})
