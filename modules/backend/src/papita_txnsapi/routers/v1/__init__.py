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
    ``/transaction-templates`` — template CRUD + upcoming dues / mark-paid (PPT-073)
        via :class:`~papita_txnsmodel.services.transactions.TransactionTemplatesService`.
    ``/movements`` — TRANSFER alias over the same transactions service.
    ``/reports`` — FR-12 read models via :class:`~papita_txnsmodel.services.reports.ReportService`.
    ``/ingestion`` — connection + run-status reads (PPT-083) via
        :class:`~papita_txnsmodel.services.ingestion_status.IngestionConnectionService` /
        :class:`~papita_txnsmodel.services.ingestion_status.IngestionRunService`.

Tenant scoping:
    Protected routes resolve the authenticated owner through ``get_current_owner`` and
    forward ``owner`` to model-layer services. Auth and health routes do not require
    an owner context.
"""

from fastapi import APIRouter, Depends

from papita_txnsapi.dependencies.services import get_db
from papita_txnsapi.routers.v1 import (
    accounts,
    ai,
    auth,
    categories,
    health,
    ingestion,
    meta,
    reports,
    transaction_templates,
    transactions,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(meta.router)
api_v1_router.include_router(auth.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(accounts.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(categories.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(transactions.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(transaction_templates.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(reports.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(ingestion.router, dependencies=[Depends(get_db)])
api_v1_router.include_router(ai.router, dependencies=[Depends(get_db)])
