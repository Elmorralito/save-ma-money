"""Model service factories and SQLAlchemy Session DI for FastAPI (PPT-097).

Wires ``Settings.DATABASE_URL`` to ``DatabaseSessionManager`` / ``get_db`` and constructs
domain services for use in v1 routers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any, TypeVar

from fastapi import Depends
from pydantic import BaseModel
from sqlmodel import Session

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsmodel.database.session import DatabaseSessionManager, get_session_manager
from papita_txnsmodel.services.account_details import TradingAccountDetailsService
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.ibkr_import import IBKRImportService
from papita_txnsmodel.services.ingestion import IngestionBridgeService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.ingestion_status import IngestionConnectionService, IngestionRunService
from papita_txnsmodel.services.reports import ReportService
from papita_txnsmodel.services.transactions import TransactionsService, TransactionTemplatesService
from papita_txnsmodel.services.users import UsersService
from papita_txnsmodel.utils.enums import FallbackAction

ServiceT = TypeVar("ServiceT", bound=BaseModel)

_transactions_service_by_manager: dict[Any, TransactionsService] = {}
_templates_service_by_manager: dict[Any, TransactionTemplatesService] = {}


def clear_transactions_service_cache() -> None:
    """Drop cached ``TransactionsService`` instances (test isolation helper)."""
    _transactions_service_by_manager.clear()


def clear_transaction_templates_service_cache() -> None:
    """Drop cached ``TransactionTemplatesService`` instances (test isolation helper)."""
    _templates_service_by_manager.clear()


async def get_db() -> AsyncIterator[Session | None]:
    """Yield a request-scoped SQLModel ``Session`` for FastAPI routes."""
    manager = get_session_manager()
    if not manager.connected(on_disconnected=FallbackAction.IGNORE):
        yield None
        return
    with manager.session_scope() as session:
        yield session


def get_session_manager_dep(settings: Annotated[Settings, Depends(get_settings)]) -> DatabaseSessionManager:
    """Return the configured ``DatabaseSessionManager`` from settings."""
    manager = settings.DATABASE_URL
    if not isinstance(manager, DatabaseSessionManager):
        raise RuntimeError("DATABASE_URL must resolve to DatabaseSessionManager")
    return manager


# Alias kept for internal router transition.
get_connector = get_session_manager_dep


def _service_factory(service_type: type[ServiceT], connector: Any) -> ServiceT:
    """Instantiate a domain service with the active database session manager."""
    return service_type.model_validate({"connector": connector})


def get_users_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> UsersService:
    """Build ``UsersService`` for authentication and tenant owner resolution."""
    return _service_factory(UsersService, connector)


def get_accounts_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> AccountsService:
    """Build ``AccountsService`` for account CRUD and listing routes."""
    return _service_factory(AccountsService, connector)


def get_categories_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> CategoriesService:
    """Build ``CategoriesService`` for category CRUD and listing routes."""
    return _service_factory(CategoriesService, connector)


def get_transaction_templates_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> TransactionTemplatesService:
    """Build ``TransactionTemplatesService`` for template CRUD and dues routes (PPT-073)."""
    key = id(connector)
    cached = _templates_service_by_manager.get(key)
    if cached is not None:
        return cached

    service = _service_factory(TransactionTemplatesService, connector)
    _templates_service_by_manager[key] = service
    return service


def get_transactions_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> TransactionsService:
    """Build ``TransactionsService`` for transaction CRUD and listing routes."""
    key = id(connector)
    cached = _transactions_service_by_manager.get(key)
    if cached is not None:
        return cached

    accounts = _service_factory(AccountsService, connector)
    categories = _service_factory(CategoriesService, connector)
    templates = get_transaction_templates_service(connector)
    service = _service_factory(TransactionsService, connector)
    wired = service.load_link_services(
        {
            "template_id": templates,
            "from_account_id": accounts,
            "to_account_id": accounts,
            "category_id": categories,
        }
    )
    _transactions_service_by_manager[key] = wired
    return wired


def get_report_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> ReportService:
    """Build ``ReportService`` for aggregated reporting endpoints."""
    return _service_factory(ReportService, connector)


def get_ingestion_connection_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> IngestionConnectionService:
    """Build ``IngestionConnectionService`` for read-only connection status routes (PPT-083)."""
    return _service_factory(IngestionConnectionService, connector)


def get_ingestion_run_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> IngestionRunService:
    """Build ``IngestionRunService`` for read-only run-status routes (PPT-083)."""
    return _service_factory(IngestionRunService, connector)


def get_ibkr_import_service(
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
) -> IBKRImportService:
    """Build ``IBKRImportService`` for Activity Statement CSV imports (PPT-101)."""
    return IBKRImportService(
        accounts_service=_service_factory(AccountsService, connector),
        trading_details_service=_service_factory(TradingAccountDetailsService, connector),
        financing_service=_service_factory(AccountFinancingService, connector),
        bridge_service=_service_factory(IngestionBridgeService, connector),
    )
