"""Ingestion connection and run-status routes — PPT-083 / #177.

Read-only status APIs under ``/ingestion``. Handlers require JWT auth via
``get_current_owner`` and delegate to model services. Workers (Prefect email
flow) own writes; this router never triggers runs or exposes OAuth/DLQ secrets.

Routes:
    ``GET /ingestion/connections`` — paginated non-secret connection metadata.
    ``GET /ingestion/connections/{connection_id}`` — single connection.
    ``GET /ingestion/runs/latest`` — most recently started run.
    ``GET /ingestion/runs`` — paginated recent runs (optional ``connection_id``).

Tenant scoping:
    Cross-tenant ids resolve as 404 (not 403). Unauthenticated requests → 401.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.services import get_ingestion_connection_service, get_ingestion_run_service
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.ingestion import IngestionConnectionResponse, IngestionRunResponse
from papita_txnsmodel.access.ingestion.dto import IngestionRunDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.ingestion_status import IngestionConnectionService, IngestionRunService

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


def _connection_not_found() -> HTTPException:
    """Build a 404 that avoids leaking cross-tenant connection existence."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion connection not found")


def _run_not_found() -> HTTPException:
    """Build a 404 that avoids leaking cross-tenant run existence."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion run not found")


def _run_filter_dto(connection_id: uuid.UUID | None) -> IngestionRunDTO | None:
    """Build a partial filter DTO for run list/count when ``connection_id`` is set."""
    if connection_id is None:
        return None
    return IngestionRunDTO.model_construct(connection_id=connection_id)


@router.get("/connections", response_model=PaginatedResponse[IngestionConnectionResponse])
def list_ingestion_connections(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> PaginatedResponse[IngestionConnectionResponse]:
    """List non-secret ingestion connections for the authenticated owner.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        connection_service: Injected connection status service.

    Returns:
        Paginated allowlisted connection resources.
    """
    total = connection_service.count_records(dto=None, owner=owner)
    rows = connection_service.list_connections(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[IngestionConnectionResponse.from_dto(row) for row in rows],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/connections/{connection_id}", response_model=IngestionConnectionResponse)
def get_ingestion_connection(
    connection_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> IngestionConnectionResponse:
    """Return one connection when owned by the caller; else 404.

    Args:
        connection_id: Connection primary key.
        owner: Authenticated tenant from JWT.
        connection_service: Injected connection status service.

    Returns:
        Allowlisted connection resource.
    """
    connection = connection_service.get_connection(owner=owner, connection_id=connection_id)
    if connection is None:
        raise _connection_not_found()
    return IngestionConnectionResponse.from_dto(connection)


@router.get("/runs/latest", response_model=IngestionRunResponse)
def get_latest_ingestion_run(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    run_service: Annotated[IngestionRunService, Depends(get_ingestion_run_service)],
    connection_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional connection filter for the latest run"),
    ] = None,
) -> IngestionRunResponse:
    """Return the most recently started run for the owner.

    Args:
        owner: Authenticated tenant from JWT.
        run_service: Injected run status service.
        connection_id: Optional filter to a single connection.

    Returns:
        Allowlisted run resource.

    Raises:
        HTTPException: 404 when no runs exist for the scope.
    """
    run = run_service.get_latest_run(owner=owner, connection_id=connection_id)
    if run is None:
        raise _run_not_found()
    return IngestionRunResponse.from_dto(run)


@router.get("/runs", response_model=PaginatedResponse[IngestionRunResponse])
def list_ingestion_runs(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    run_service: Annotated[IngestionRunService, Depends(get_ingestion_run_service)],
    connection_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional filter by connection id"),
    ] = None,
) -> PaginatedResponse[IngestionRunResponse]:
    """List recent ingestion runs for the authenticated owner.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        run_service: Injected run status service.
        connection_id: Optional filter by connection id.

    Returns:
        Paginated allowlisted run resources, newest first.
    """
    filter_dto = _run_filter_dto(connection_id)
    total = run_service.count_records(dto=filter_dto, owner=owner)
    rows = run_service.list_runs(
        owner=owner,
        connection_id=connection_id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[IngestionRunResponse.from_dto(row) for row in rows],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
