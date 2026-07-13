"""Transaction CRUD routes — PPT-037.

Exposes tenant-scoped INCOME/EXPENSE transaction management under ``/transactions``.
All handlers require JWT auth via ``get_current_owner`` and delegate persistence to
:class:`~papita_txnsmodel.services.transactions.TransactionsService`. TRANSFER rows
are excluded from default list responses; use ``/movements`` or
``?transaction_type=transfer`` to include them.

Routes:
    ``GET /transactions`` — paginated list with G4 filters; excludes TRANSFER by default.
    ``GET /transactions/{transaction_id}`` — single transaction with linked names.
    ``POST /transactions`` — create INCOME/EXPENSE row.
    ``POST /transactions/bulk`` — bulk create INCOME/EXPENSE rows.
    ``PUT /transactions/{transaction_id}`` — update tenant-owned transaction.
    ``DELETE /transactions/{transaction_id}`` — soft-delete tenant-owned transaction.
    ``POST /transactions/{transaction_id}/split`` — deferred 501 (v4).

Tenant scoping:
    Every mutating and read path passes ``owner=`` so ledger rows never leak across
    tenants. Cross-tenant ids resolve as not found (404).
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
    """Build a 404 response for a missing or inaccessible transaction.

    Returns:
        HTTPException: 404 with a generic detail that avoids leaking cross-tenant
            existence of ledger rows.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key.

    Args:
        value: Primary key from a DTO that may not yet be persisted.

    Returns:
        The non-``None`` UUID value.

    Raises:
        HTTPException: 404 when ``value`` is ``None``.
    """
    if value is None:
        raise _transaction_not_found()
    return value


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key.

    Args:
        owner: Authenticated tenant DTO from JWT resolution.

    Returns:
        Non-null tenant UUID used when constructing create DTOs.

    Raises:
        HTTPException: 401 when ``owner.id`` is missing (invalid auth context).
    """
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
    """List tenant transactions with optional G4 filters.

    By default TRANSFER rows are excluded (``exclude_transfer=True``) unless the
    client filters ``transaction_type=transfer``.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        transactions_service: Injected service providing ``list_transactions``.
        filters: Bundled query parameters mapped to service kwargs.

    Returns:
        Paginated ``TransactionResponse`` items owned by ``owner``.
    """
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
    """Create multiple INCOME/EXPENSE transactions for the authenticated tenant.

    Each item is created independently; ``ValueError`` / ``TypeError`` on an item
    increments ``failed`` without aborting the remainder of the batch.

    Args:
        body: Bulk payload containing one or more ``TransactionCreate`` items.
        owner: Authenticated tenant that will own every created row.
        transactions_service: Injected service used for per-item ``create``.

    Returns:
        TransactionBulkResponse with counts and successfully created items.

    Raises:
        HTTPException: 401 when the owner context lacks a primary key.
    """
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
    """Defer transaction split until v4 ``transaction_splits`` (MVP stub).

    Args:
        transaction_id: Path identifier reserved for a future split target row.

    Returns:
        DeferredResponse explaining that split is not implemented in MVP.
    """
    del transaction_id
    return _DEFERRED_SPLIT


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> TransactionResponse:
    """Retrieve a single tenant-owned transaction with linked names.

    Args:
        transaction_id: Ledger primary key from the path.
        owner: Authenticated tenant from JWT.
        transactions_service: Injected service for owner-scoped get-by-id.

    Returns:
        TransactionResponse including account/category names when linked DTOs load.

    Raises:
        HTTPException: 404 when the row is missing or not owned by ``owner``.
    """
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
    """Create an INCOME or EXPENSE transaction for the authenticated tenant.

    Args:
        body: Create payload (account, category, type, amount, date, optional fields).
        owner: Authenticated tenant that will own the new row.
        transactions_service: Injected service providing ``create``.

    Returns:
        TransactionResponse for the persisted row.

    Raises:
        HTTPException: 401 when owner id is missing; domain errors may surface as
            400 via the global ``ValueError`` handler.
    """
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
    """Update a tenant-owned INCOME/EXPENSE transaction via upsert.

    TRANSFER rows must be updated through ``PUT /movements`` instead.

    Args:
        transaction_id: Ledger primary key from the path.
        body: Partial update fields applied onto the existing DTO.
        owner: Authenticated tenant that must own the row.
        transactions_service: Injected service for get and upsert.

    Returns:
        TransactionResponse for the updated row.

    Raises:
        HTTPException: 404 when missing; 422 when the row is a TRANSFER.
    """
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
    """Soft-delete a tenant-owned transaction.

    Args:
        transaction_id: Ledger primary key from the path.
        owner: Authenticated tenant that must own the row.
        transactions_service: Injected service providing soft ``delete``.

    Raises:
        HTTPException: 404 when the row is missing or not owned by ``owner``.
    """
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    transactions_service.delete(obj=TransactionsDTO.model_construct(id=transaction_id), owner=owner)
