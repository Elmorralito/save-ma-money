"""Version 1 API router aggregator.

Mounts domain routers under a single :class:`fastapi.APIRouter` for inclusion in the
application. Registration order places unauthenticated probes first, then auth, then
tenant-scoped CRUD routes.

Routes exposed (prefix relative to app mount):
    ``/health`` — liveness, readiness, database, Auth, and composite health (no tenant scope).
    ``/auth`` — register, login, profile; refresh/logout via Supabase Auth sessions.
    ``/bff/auth`` — HttpOnly cookie session (PPT-049); JWTs stay server-side.
    ``/accounts`` — tenant-scoped account CRUD via :class:`~papita_txnsmodel.services.accounts.AccountsService`.
    ``/categories`` — tenant + global seed categories via
        :class:`~papita_txnsmodel.services.categories.CategoriesService`.
    ``/transactions`` — tenant-scoped INCOME/EXPENSE ledger via
        :class:`~papita_txnsmodel.services.transactions.TransactionsService`.
    ``/movements`` — TRANSFER alias over the same transactions service.
    ``/reports`` — FR-12 read models via :class:`~papita_txnsmodel.services.reports.ReportService`.
    ``/budgets`` — placeholder 501 responses (FR-09 deferred to v4.1).

Tenant scoping:
    Protected routes resolve the authenticated owner through ``get_current_owner`` and
    forward ``owner`` to model-layer services. Auth and health routes do not require
    an owner context.
"""

from fastapi import APIRouter

from papita_txnsapi.routers.v1 import (
    accounts,
    auth,
    bff_auth,
    budgets,
    categories,
    health,
    meta,
    movements,
    reports,
    transactions,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(meta.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(bff_auth.router)
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(transactions.router)
api_v1_router.include_router(movements.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(budgets.router)
