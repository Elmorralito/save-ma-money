"""Account CRUD routes — PPT-036.

Exposes tenant-scoped account management under ``/accounts``. All handlers require an
authenticated owner via ``get_current_owner`` and delegate persistence to
:class:`~papita_txnsmodel.services.accounts.AccountsService`.

Routes:
    ``GET /accounts`` — paginated list with optional kind, ledger side, and active filters.
    ``GET /accounts/{account_id}`` — single account with extension details and balance.
    ``POST /accounts`` — create account and optional kind-specific extension row.
    ``PUT /accounts/{account_id}`` — update account and optional extension row.
    ``DELETE /accounts/{account_id}`` — soft-delete tenant-owned account.
    ``GET /accounts/{account_id}/balance`` — balance from ``account_balances`` MV.

Tenant scoping:
    Every handler passes ``owner`` to service methods so queries and mutations are
    limited to the authenticated tenant's records.

Service delegation:
    List/read operations use ``get_records``, ``get``, and ``get_with_extension``.
    Mutations use ``create_account``, ``update_account``, and ``delete``.
    Balances are read via ``get_balance`` and the nested ``balances_service`` when present.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    bump_cache_versions,
    get_versioned_cached_json,
    set_versioned_cached_json,
    ttl_for_namespace,
)
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_accounts_service
from papita_txnsapi.schemas.accounts import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    BalanceResponse,
    accounts_from_dataframe,
    balances_by_account_id,
    effective_account_balance,
)
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.converters import parse_account_kind, parse_ledger_side
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.accounts import AccountsService

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


def _account_not_found() -> HTTPException:
    """Build a 404 response for a missing or inaccessible account.

    Returns:
        HTTPException: 404 with a generic "Account not found" detail to avoid leaking
            cross-tenant existence.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


def _require_uuid(value: uuid.UUID | None, *, not_found: HTTPException | None = None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key.

    Args:
        value: Primary key from a DTO that may not yet be persisted.
        not_found: Optional exception to raise instead of the default account-not-found
            response.

    Returns:
        The non-``None`` UUID value.

    Raises:
        HTTPException: When ``value`` is ``None``.
    """
    if value is None:
        raise not_found or _account_not_found()
    return value


def _build_account_filter_dto(
    *,
    account_kind: str | None,
    ledger_side: str | None,
    is_active: bool | None,
) -> AccountsDTO | None:
    """Build a filter DTO using only explicitly set query parameters.

    Args:
        account_kind: Optional account kind slug to parse into an enum value.
        ledger_side: Optional asset/liability slug to parse into an enum value.
        is_active: Optional active flag; omitted parameters are not applied.

    Returns:
        A partial :class:`~papita_txnsmodel.access.accounts.dto.AccountsDTO` for
        service filtering, or ``None`` when no filters were provided.
    """
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
    """Return MV balance for an account, falling back to ``initial_value`` when MV is empty.

    Args:
        accounts_service: Tenant-scoped accounts service with optional balances helper.
        owner: Authenticated tenant used for balance lookups.
        account_id: Target account primary key.
        account: Optional account DTO used to apply ``effective_account_balance`` fallback
            logic when the materialized view has no row.

    Returns:
        Numeric balance for the account, preferring MV data when available.
    """
    row = accounts_service.get_balance(owner=owner, account_id=account_id)
    mv_balance = float(row.balance) if row is not None else None
    if account is not None:
        return effective_account_balance(account, mv_balance=mv_balance)
    if mv_balance is not None:
        return mv_balance
    return 0.0


def _invalidate_account_caches(redis: Redis | None, owner: UsersDTO) -> None:
    """Bump accounts + reports cache versions after account or balance-affecting writes."""
    bump_cache_versions(redis, owner.id, CacheNamespace.ACCOUNTS, CacheNamespace.REPORTS)


@router.get("", response_model=PaginatedResponse[AccountResponse])
def list_accounts(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
    *,
    account_kind: Annotated[str | None, Query(description="Filter by account kind slug")] = None,
    ledger_side: Annotated[str | None, Query(description="Filter by asset or liability")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
) -> PaginatedResponse[AccountResponse]:
    """List tenant accounts with optional filters and balances from ``account_balances``.

    When Redis is enabled, responses are cached per owner and query params (cache-aside).
    Mutations bump the accounts namespace version so prior entries miss.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        accounts_service: Injected accounts service scoped to the request lifecycle.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.
        account_kind: Optional filter by account kind slug.
        ledger_side: Optional filter by asset or liability slug.
        is_active: Optional filter by active status.

    Returns:
        Paginated account rows enriched with effective balances per item.
    """
    cache_params = {
        "skip": pagination.skip,
        "limit": pagination.limit,
        "account_kind": account_kind,
        "ledger_side": ledger_side,
        "is_active": is_active,
    }
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.ACCOUNTS, "accounts:list", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return PaginatedResponse[AccountResponse].model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    filter_dto = _build_account_filter_dto(
        account_kind=account_kind,
        ledger_side=ledger_side,
        is_active=is_active,
    )
    page_df, total = accounts_service.list_accounts(
        owner=owner,
        dto=filter_dto,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    accounts = accounts_from_dataframe(page_df)

    # Page-scoped MV load: avoid fetching the whole tenant's balances on list.
    account_ids = [account.id for account in accounts if account.id is not None]
    if accounts_service.balances_service is None or not account_ids:
        balance_map = {}
    else:
        balances_df = accounts_service.balances_service.get_balances(owner=owner, account_ids=account_ids)
        balance_map = balances_by_account_id(balances_df)

    items = [
        AccountResponse.from_dto(account, balance=effective_account_balance(account, balance_map=balance_map))
        for account in accounts
    ]
    payload: PaginatedResponse[AccountResponse] = PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.ACCOUNTS,
            "accounts:list",
            cache_params,
            value=payload.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.ACCOUNTS),
            version=cache_version,
        )
    return payload


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> AccountResponse:
    """Retrieve a single account with extension details and current balance.

    Args:
        account_id: Primary key of the account to fetch.
        owner: Authenticated tenant from JWT.
        accounts_service: Injected accounts service scoped to the request lifecycle.

    Returns:
        Account payload including kind-specific extension fields and computed balance.

    Raises:
        HTTPException: 404 when the account is missing or not owned by the tenant.
    """
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
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> AccountResponse:
    """Create an account and optional kind-specific extension row.

    Args:
        body: Validated create payload including core account fields and extension data.
        owner: Authenticated tenant from JWT; used as ``owner_id`` on the new record.
        accounts_service: Injected accounts service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        Created account with extension details and initial effective balance.

    Raises:
        HTTPException: 404 when the owner DTO lacks a persisted id (unexpected).
        ValueError: Propagated from the service layer on invalid business input.
    """
    account_dto = body.to_accounts_dto(owner_id=_require_uuid(owner.id))
    created, extension = accounts_service.create_account(
        obj=account_dto,
        extension=body.extension_payload(),
        owner=owner,
    )
    created_id = _require_uuid(created.id)
    balance = _balance_for_account(accounts_service, owner, created_id, account=created)
    _invalidate_account_caches(redis, owner)
    return AccountResponse.from_dto(created, balance=balance, extension=extension)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> AccountResponse:
    """Update an account and optional extension row.

    Args:
        account_id: Primary key of the account to update.
        body: Partial update payload merged onto the existing DTO.
        owner: Authenticated tenant from JWT.
        accounts_service: Injected accounts service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        Updated account with extension details and current effective balance.

    Raises:
        HTTPException: 404 when the account is missing or not owned by the tenant.
        ValueError: Propagated from the service layer on invalid business input.
    """
    existing, existing_extension = accounts_service.get_with_extension(obj=account_id, owner=owner)
    if existing is None:
        raise _account_not_found()

    merged = body.apply_to(existing)
    updated, upserted_extension = accounts_service.update_account(
        obj=merged,
        extension=body.extension_payload(existing.account_kind),
        owner=owner,
    )
    updated_id = _require_uuid(updated.id)
    # Reuse prior extension when the update did not touch extension fields.
    extension = upserted_extension if upserted_extension is not None else existing_extension
    balance = _balance_for_account(accounts_service, owner, updated_id, account=updated)
    _invalidate_account_caches(redis, owner)
    return AccountResponse.from_dto(updated, balance=balance, extension=extension)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Soft-delete an account owned by the authenticated tenant.

    Args:
        account_id: Primary key of the account to delete.
        owner: Authenticated tenant from JWT.
        accounts_service: Injected accounts service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        ``None``; response body is empty on success.

    Raises:
        HTTPException: 404 when the account is missing or not owned by the tenant.
    """
    existing = accounts_service.get(obj=account_id, owner=owner)
    if existing is None:
        raise _account_not_found()
    accounts_service.delete(obj=AccountsDTO.model_construct(id=account_id), owner=owner)
    _invalidate_account_caches(redis, owner)


@router.get("/{account_id}/balance", response_model=BalanceResponse)
def get_account_balance(
    account_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
) -> BalanceResponse:
    """Return the current balance from the ``account_balances`` materialized view.

    Args:
        account_id: Primary key of the account whose balance is requested.
        owner: Authenticated tenant from JWT.
        accounts_service: Injected accounts service scoped to the request lifecycle.

    Returns:
        Balance snapshot with currency; falls back to ``initial_value`` when MV has no row.

    Raises:
        HTTPException: 404 when the account is missing or not owned by the tenant.
    """
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
