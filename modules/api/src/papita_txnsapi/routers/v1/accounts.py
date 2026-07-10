"""Account CRUD routes — PPT-036."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.services import get_accounts_service
from papita_txnsapi.schemas.accounts import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    BalanceResponse,
    accounts_from_dataframe,
    balances_by_account_id,
    effective_account_balance,
    paginate_dataframe,
)
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.converters import parse_account_kind, parse_ledger_side
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.accounts import AccountsService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def _account_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


def _require_uuid(value: uuid.UUID | None, *, not_found: HTTPException | None = None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key."""
    if value is None:
        raise not_found or _account_not_found()
    return value


def _build_account_filter_dto(
    *,
    account_kind: str | None,
    ledger_side: str | None,
    is_active: bool | None,
) -> AccountsDTO | None:
    """Build a filter DTO using only explicitly set query parameters."""
    filter_fields: dict[str, object] = {}
    if account_kind is not None:
        filter_fields["account_kind"] = parse_account_kind(account_kind)
    if ledger_side is not None:
        filter_fields["ledger_side"] = parse_ledger_side(ledger_side)
    if is_active is not None:
        filter_fields["active"] = is_active
    if not filter_fields:
        return None
    return AccountsDTO.model_construct(**filter_fields)


def _balance_for_account(
    accounts_service: AccountsService,
    owner: UsersDTO,
    account_id: uuid.UUID,
    account: AccountsDTO | None = None,
) -> float:
    """Return MV balance for an account, falling back to ``initial_value`` when MV is empty."""
    row = accounts_service.get_balance(owner=owner, account_id=account_id)
    mv_balance = float(row.balance) if row is not None else None
    if account is not None:
        return effective_account_balance(account, mv_balance=mv_balance)
    if mv_balance is not None:
        return mv_balance
    return 0.0


@router.get("", response_model=PaginatedResponse[AccountResponse])
def list_accounts(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    *,
    account_kind: Annotated[str | None, Query(description="Filter by account kind slug")] = None,
    ledger_side: Annotated[str | None, Query(description="Filter by asset or liability")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
) -> PaginatedResponse[AccountResponse]:
    """List tenant accounts with optional filters and balances from ``account_balances``."""
    filter_dto = _build_account_filter_dto(
        account_kind=account_kind,
        ledger_side=ledger_side,
        is_active=is_active,
    )
    records_df = accounts_service.get_records(filter_dto, owner=owner)
    page_df, total = paginate_dataframe(records_df, pagination.skip, pagination.limit)
    accounts = accounts_from_dataframe(page_df)

    balances_df = (
        accounts_service.balances_service.get_balances(owner=owner) if accounts_service.balances_service else None
    )
    balance_map = balances_by_account_id(balances_df) if balances_df is not None else {}

    items = [
        AccountResponse.from_dto(account, balance=effective_account_balance(account, balance_map=balance_map))
        for account in accounts
    ]
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> AccountResponse:
    """Retrieve a single account with extension details and current balance."""
    account, extension = accounts_service.get_with_extension(obj=account_id, owner=owner)
    if account is None:
        raise _account_not_found()
    balance = _balance_for_account(
        accounts_service,
        owner,
        _require_uuid(account.id),
        account=account,
    )
    return AccountResponse.from_dto(account, balance=balance, extension=extension)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
def create_account(
    body: AccountCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> AccountResponse:
    """Create an account and optional kind-specific extension row."""
    account_dto = body.to_accounts_dto(owner_id=_require_uuid(owner.id))
    created = accounts_service.create_account(
        obj=account_dto,
        extension=body.extension_payload(),
        owner=owner,
    )
    created_id = _require_uuid(created.id)
    _, extension = accounts_service.get_with_extension(obj=created_id, owner=owner)
    balance = _balance_for_account(accounts_service, owner, created_id, account=created)
    return AccountResponse.from_dto(created, balance=balance, extension=extension)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> AccountResponse:
    """Update an account and optional extension row."""
    existing, _extension = accounts_service.get_with_extension(obj=account_id, owner=owner)
    if existing is None:
        raise _account_not_found()

    merged = body.apply_to(existing)
    updated = accounts_service.update_account(
        obj=merged,
        extension=body.extension_payload(existing.account_kind),
        owner=owner,
    )
    updated_id = _require_uuid(updated.id)
    _, extension = accounts_service.get_with_extension(obj=updated_id, owner=owner)
    balance = _balance_for_account(accounts_service, owner, updated_id, account=updated)
    return AccountResponse.from_dto(updated, balance=balance, extension=extension)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> None:
    """Soft-delete an account owned by the authenticated tenant."""
    existing = accounts_service.get(obj=account_id, owner=owner)
    if existing is None:
        raise _account_not_found()
    accounts_service.delete(obj=AccountsDTO.model_construct(id=account_id), owner=owner)


@router.get("/{account_id}/balance", response_model=BalanceResponse)
def get_account_balance(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> BalanceResponse:
    """Return the current balance from the ``account_balances`` materialized view."""
    existing = accounts_service.get(obj=account_id, owner=owner)
    if existing is None:
        raise _account_not_found()

    row = accounts_service.get_balance(owner=owner, account_id=account_id)
    if row is None:
        return BalanceResponse(
            account_id=account_id,
            balance=effective_account_balance(existing),
            currency=existing.currency,
            as_of=None,
        )
    return BalanceResponse.from_balance_dto(row)
