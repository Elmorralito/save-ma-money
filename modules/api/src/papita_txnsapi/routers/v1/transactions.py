"""Transaction CRUD routes — PPT-037.

Exposes tenant-scoped INCOME/EXPENSE transaction management under ``/transactions``.
TRANSFER rows are excluded from default list responses; use ``/movements`` or
``?transaction_type=transfer`` to include them.

Routes:
    ``GET /transactions`` — paginated list with G4 filters; excludes TRANSFER by default.
    ``GET /transactions/{transaction_id}`` — single transaction with linked names.
    ``POST /transactions`` — create INCOME/EXPENSE row.
    ``POST /transactions/bulk`` — bulk create INCOME/EXPENSE rows.
    ``PUT /transactions/{transaction_id}`` — update tenant-owned transaction.
    ``DELETE /transactions/{transaction_id}`` — soft-delete tenant-owned transaction.
    ``POST /transactions/{transaction_id}/split`` — deferred 501 (v4).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.services import get_transactions_service
from papita_txnsapi.schemas.common import DeferredResponse, PaginatedResponse
from papita_txnsapi.schemas.query_params import TransactionListQuery, get_transaction_list_query
from papita_txnsapi.schemas.transactions import (
    TransactionBulkCreate,
    TransactionBulkResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    transactions_from_dataframe,
)
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind
from papita_txnsmodel.services.transactions import TransactionsService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

_DEFERRED_SPLIT = DeferredResponse(deferred_reason="Transaction split deferred to v4 transaction_splits")


def _transaction_not_found() -> HTTPException:
    """Build a 404 response for a missing or inaccessible transaction."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key."""
    if value is None:
        raise _transaction_not_found()
    return value


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key."""
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


@router.get("", response_model=PaginatedResponse[TransactionResponse])
def list_transactions(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    filters: Annotated[TransactionListQuery, Depends(get_transaction_list_query)],
) -> PaginatedResponse[TransactionResponse]:
    """List tenant transactions with optional filters."""
    records_df, total = transactions_service.list_transactions(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
        **filters.service_kwargs(),
    )
    items = [TransactionResponse.from_dto(txn) for txn in transactions_from_dataframe(records_df)]
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=TransactionBulkResponse)
def bulk_create_transactions(
    body: TransactionBulkCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> TransactionBulkResponse:
    """Create multiple INCOME/EXPENSE transactions."""
    owner_id = _require_owner_id(owner)
    created_items: list[TransactionResponse] = []
    failed = 0

    for item in body.transactions:
        try:
            dto = item.to_transactions_dto(owner_id=owner_id)
            result = transactions_service.create(obj=dto, owner=owner)
            created_items.append(TransactionResponse.from_dto(result))
        except (ValueError, TypeError):
            failed += 1

    return TransactionBulkResponse(created=len(created_items), failed=failed, transactions=created_items)


@router.post("/{transaction_id}/split", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def split_transaction(transaction_id: uuid.UUID) -> DeferredResponse:
    """Split a transaction — deferred post-MVP (v4)."""
    del transaction_id
    return _DEFERRED_SPLIT


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> TransactionResponse:
    """Retrieve a single transaction with linked account and category names."""
    transaction = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=True)
    if transaction is None:
        raise _transaction_not_found()
    return TransactionResponse.from_dto(transaction, include_names=True)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
def create_transaction(
    body: TransactionCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> TransactionResponse:
    """Create an INCOME or EXPENSE transaction."""
    dto = body.to_transactions_dto(owner_id=_require_owner_id(owner))
    created = transactions_service.create(obj=dto, owner=owner)
    return TransactionResponse.from_dto(created)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> TransactionResponse:
    """Update a tenant-owned INCOME/EXPENSE transaction."""
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    if existing.transaction_kind == TransactionKind.TRANSFER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use PUT /movements to update transfer transactions.",
        )

    merged = body.apply_to(existing)
    updated = transactions_service.create(obj=merged, owner=owner)
    return TransactionResponse.from_dto(updated)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> None:
    """Soft-delete a tenant-owned transaction."""
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    transactions_service.delete(obj=TransactionsDTO.model_construct(id=transaction_id), owner=owner)
