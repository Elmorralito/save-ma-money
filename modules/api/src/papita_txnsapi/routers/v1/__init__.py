"""Version 1 API router aggregator.

Mounts domain routers under a single :class:`fastapi.APIRouter` for inclusion in the
application. Registration order places unauthenticated probes first, then auth, then
tenant-scoped CRUD routes.

Routes exposed (prefix relative to app mount):
    ``/health`` — liveness, readiness, and composite health (no tenant scope).
    ``/auth`` — register, login, profile; refresh/logout deferred (FR-11).
    ``/accounts`` — tenant-scoped account CRUD via :class:`~papita_txnsmodel.services.accounts.AccountsService`.
    ``/categories`` — tenant + global seed categories via
        :class:`~papita_txnsmodel.services.categories.CategoriesService`.
    ``/budgets`` — placeholder 501 responses (FR-09 deferred to v4.1).

Tenant scoping:
    Protected routes resolve the authenticated owner through ``get_current_owner`` and
    forward ``owner`` to model-layer services. Auth and health routes do not require
    an owner context.
"""

from fastapi import APIRouter

from papita_txnsapi.routers.v1 import accounts, auth, budgets, categories, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(budgets.router)
