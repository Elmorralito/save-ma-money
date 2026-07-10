"""Deferred budget endpoints — return 501 in MVP (FR-09).

Placeholder router reserving the ``/budgets`` URL space for v4.1 budget features.
All handlers respond with HTTP 501 and a :class:`~papita_txnsapi.schemas.common.DeferredResponse`
payload; no model services are invoked and no tenant scoping applies yet.

Routes (all deferred):
    ``GET /budgets`` — list budgets.
    ``GET /budgets/{budget_id}`` — fetch one budget.
    ``POST /budgets`` — create budget.
    ``PUT /budgets/{budget_id}`` — update budget.
    ``DELETE /budgets/{budget_id}`` — delete budget.
    ``GET /budgets/{budget_id}/summary`` — budget summary rollup.
    ``POST /budgets/{budget_id}/allocations`` — update category allocations.

Service delegation:
    None in MVP. Future implementation will delegate to a budgets service in
    ``papita_txnsmodel`` with ``owner`` scoping consistent with accounts/categories.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from papita_txnsapi.schemas.common import DeferredResponse

router = APIRouter(prefix="/budgets", tags=["Budgets (deferred)"])

_DEFERRED = DeferredResponse(deferred_reason="FR-09 budgets deferred to v4.1")


def _not_implemented() -> DeferredResponse:
    """Return the shared deferred payload for all budget stubs.

    Returns:
        DeferredResponse: Standard FR-09 deferral message for budget endpoints.
    """
    return _DEFERRED


@router.get("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def list_budgets() -> DeferredResponse:
    """List budgets — deferred post-MVP.

    Returns:
        DeferredResponse: Explains that budget listing is not available in MVP.
    """
    return _not_implemented()


@router.get("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget(budget_id: str) -> DeferredResponse:
    """Get budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget retrieval is not available in MVP.
    """
    return _not_implemented()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_budget() -> DeferredResponse:
    """Create budget — deferred post-MVP.

    Returns:
        DeferredResponse: Explains that budget creation is not available in MVP.
    """
    return _not_implemented()


@router.put("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget(budget_id: str) -> DeferredResponse:
    """Update budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget updates are not available in MVP.
    """
    return _not_implemented()


@router.delete("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def delete_budget(budget_id: str) -> DeferredResponse:
    """Delete budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget deletion is not available in MVP.
    """
    return _not_implemented()


@router.get("/{budget_id}/summary", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget_summary(budget_id: str) -> DeferredResponse:
    """Budget summary — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget summaries are not available in MVP.
    """
    return _not_implemented()


@router.post("/{budget_id}/allocations", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget_allocations(budget_id: str) -> DeferredResponse:
    """Budget allocations — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that allocation updates are not available in MVP.
    """
    return _not_implemented()
