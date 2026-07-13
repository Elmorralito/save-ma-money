"""Movement (TRANSFER alias) routes — PPT-037.

Exposes tenant-scoped transfer management under ``/movements``. All rows persist
in ``transactions`` with ``transaction_kind = TRANSFER`` via
:class:`~papita_txnsmodel.services.transactions.TransactionsService` transfer helpers.

Routes:
    ``GET /movements`` — paginated transfer list with optional filters.
    ``GET /movements/{movement_id}`` — single transfer with linked account names.
    ``POST /movements`` — create transfer; ``scheduled: true`` leaves status PENDING.
    ``PUT /movements/{movement_id}`` — update a PENDING transfer.
    ``DELETE /movements/{movement_id}`` — cancel a PENDING transfer.
    ``POST /movements/{movement_id}/execute`` — complete a PENDING transfer.
"""

from __future__ import annotations

import uuid
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.services import get_accounts_service, get_transactions_service
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.movements import (
    MovementCreate,
    MovementExecuteResponse,
    MovementResponse,
    MovementUpdate,
    movements_from_dataframe,
)
from papita_txnsapi.schemas.query_params import MovementListQuery, get_movement_list_query
from papita_txnsapi.schemas.transactions import _relation_uuid
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.transactions import TransactionsService

router = APIRouter(prefix="/movements", tags=["Movements"])


def _movement_not_found() -> HTTPException:
    """Build a 404 response for a missing or inaccessible movement."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key."""
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


def _require_transfer(
    transactions_service: TransactionsService,
    movement_id: uuid.UUID,
    owner: UsersDTO,
) -> TransactionsDTO:
    """Load a tenant-owned TRANSFER row or raise 404."""
    transfer = transactions_service.get(obj=movement_id, owner=owner, include_linked_dtos=False)
    if transfer is None or transfer.transaction_kind != TransactionKind.TRANSFER:
        raise _movement_not_found()
    return transfer


def _validate_transfer_accounts(
    accounts_service: AccountsService,
    owner: UsersDTO,
    *,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    currency: str,
) -> None:
    """Ensure both accounts exist for the tenant and share the requested currency."""
    if source_account_id == destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source and destination accounts must differ.",
        )

    source = accounts_service.get(obj=source_account_id, owner=owner)
    destination = accounts_service.get(obj=destination_account_id, owner=owner)
    if source is None or destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    normalized_currency = currency.upper()
    if source.currency != destination.currency or source.currency != normalized_currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Currency must match both accounts.",
        )


def _require_pending(transfer: TransactionsDTO) -> None:
    """Reject mutations on non-pending transfers."""
    if transfer.status != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending movements can be modified.",
        )


@router.get("", response_model=PaginatedResponse[MovementResponse])
def list_movements(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    filters: Annotated[MovementListQuery, Depends(get_movement_list_query)],
) -> PaginatedResponse[MovementResponse]:
    """List tenant transfer rows."""
    records_df, total = transactions_service.list_transfers(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
        **filters.service_kwargs(),
    )
    items = [MovementResponse.from_dto(txn) for txn in movements_from_dataframe(records_df)]
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/{movement_id}", response_model=MovementResponse)
def get_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> MovementResponse:
    """Retrieve a single transfer with linked account names."""
    transfer = transactions_service.get(obj=movement_id, owner=owner, include_linked_dtos=True)
    if transfer is None or transfer.transaction_kind != TransactionKind.TRANSFER:
        raise _movement_not_found()
    return MovementResponse.from_dto(transfer, include_names=True)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MovementResponse)
def create_movement(
    body: MovementCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> MovementResponse:
    """Create a transfer between two tenant-owned accounts."""
    _validate_transfer_accounts(
        accounts_service,
        owner,
        source_account_id=body.source_account_id,
        destination_account_id=body.destination_account_id,
        currency=body.currency,
    )
    dto = body.to_transactions_dto(owner_id=_require_owner_id(owner))
    created = transactions_service.create_transfer(obj=dto, owner=owner)
    if not body.scheduled:
        created = transactions_service.complete_transfer(transaction_id=created, owner=owner)
    return MovementResponse.from_dto(created)


@router.put("/{movement_id}", response_model=MovementResponse)
def update_movement(
    movement_id: uuid.UUID,
    body: MovementUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> MovementResponse:
    """Update a pending transfer."""
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)

    merged = body.apply_to(existing)
    source_id = _relation_uuid(merged.from_account_id)
    destination_id = _relation_uuid(merged.to_account_id)
    if source_id is None or destination_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid account legs.")

    _validate_transfer_accounts(
        accounts_service,
        owner,
        source_account_id=source_id,
        destination_account_id=destination_id,
        currency=merged.currency,
    )
    updated = transactions_service.create(obj=merged, owner=owner)
    return MovementResponse.from_dto(updated)


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> None:
    """Cancel a pending transfer (status=CANCELLED)."""
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)
    try:
        transactions_service.cancel(transaction_id=movement_id, owner=owner)
    except ValueError as exc:
        raise _movement_not_found() from exc


@router.post("/{movement_id}/execute", response_model=MovementExecuteResponse)
def execute_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> MovementExecuteResponse:
    """Complete a pending scheduled transfer."""
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)
    try:
        completed = transactions_service.complete_transfer(transaction_id=movement_id, owner=owner)
    except ValueError as exc:
        raise _movement_not_found() from exc

    executed_at = completed.transaction_ts
    if executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=timezone.utc)
    return MovementExecuteResponse(
        id=_require_uuid(completed.id),
        status="completed",
        executed_at=executed_at,
    )


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key."""
    if value is None:
        raise _movement_not_found()
    return value
