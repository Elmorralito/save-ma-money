"""Model service factories for FastAPI dependency injection.

Wires ``Settings.DATABASE_URL`` to the model ``SQLDatabaseConnector`` and constructs
layered ``BaseService`` subclasses for use in v1 routers. Each ``get_*_service``
function is a thin FastAPI dependency over a shared connector.

Key exports:
    get_connector: Resolve and validate the SQLAlchemy connector class.
    get_users_service, get_accounts_service, get_categories_service,
    get_transactions_service, get_report_service: Domain service factories.
"""

from __future__ import annotations

from typing import Annotated, Type, TypeVar

from fastapi import Depends
from pydantic import BaseModel

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.reports import ReportService
from papita_txnsmodel.services.transactions import TransactionsService
from papita_txnsmodel.services.users import UsersService

ServiceT = TypeVar("ServiceT", bound=BaseModel)


def get_connector(settings: Annotated[Settings, Depends(get_settings)]) -> Type[SQLDatabaseConnector]:
    """Return the model ``SQLDatabaseConnector`` class configured from settings.

    Args:
        settings: Injected API settings whose ``DATABASE_URL`` resolves to a connector.

    Returns:
        ``SQLDatabaseConnector`` subclass bound to the configured database URL.

    Raises:
        RuntimeError: When ``DATABASE_URL`` does not resolve to a connector class.
    """
    connector = settings.DATABASE_URL
    if not isinstance(connector, type) or not issubclass(connector, SQLDatabaseConnector):
        raise RuntimeError("DATABASE_URL must resolve to SQLDatabaseConnector")
    return connector


def _service_factory(service_type: type[ServiceT], connector: Type[SQLDatabaseConnector]) -> ServiceT:
    """Instantiate a model service with the shared database connector.

    Args:
        service_type: ``BaseService`` subclass to construct.
        connector: Model connector class injected into the service payload.

    Returns:
        Validated service instance ready for handler/repository calls.
    """
    return service_type.model_validate({"connector": connector})


def get_users_service(connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)]) -> UsersService:
    """Build ``UsersService`` for authentication and tenant owner resolution.

    Args:
        connector: Injected model database connector.

    Returns:
        Configured ``UsersService`` instance.
    """
    return _service_factory(UsersService, connector)


def get_accounts_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> AccountsService:
    """Build ``AccountsService`` for account CRUD and listing routes.

    Args:
        connector: Injected model database connector.

    Returns:
        Configured ``AccountsService`` instance.
    """
    return _service_factory(AccountsService, connector)


def get_categories_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> CategoriesService:
    """Build ``CategoriesService`` for category CRUD and listing routes.

    Args:
        connector: Injected model database connector.

    Returns:
        Configured ``CategoriesService`` instance.
    """
    return _service_factory(CategoriesService, connector)


def get_transactions_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> TransactionsService:
    """Build ``TransactionsService`` for transaction CRUD and listing routes.

    Args:
        connector: Injected model database connector.

    Returns:
        Configured ``TransactionsService`` instance.
    """
    return _service_factory(TransactionsService, connector)


def get_report_service(connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)]) -> ReportService:
    """Build ``ReportService`` for aggregated reporting endpoints.

    Args:
        connector: Injected model database connector.

    Returns:
        Configured ``ReportService`` instance.
    """
    return _service_factory(ReportService, connector)
