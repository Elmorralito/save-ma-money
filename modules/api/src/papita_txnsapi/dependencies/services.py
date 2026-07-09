"""Model service factories for FastAPI dependency injection."""

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
    """Return the model SQLDatabaseConnector class configured from Settings."""
    connector = settings.DATABASE_URL
    if not isinstance(connector, type) or not issubclass(connector, SQLDatabaseConnector):
        raise RuntimeError("DATABASE_URL must resolve to SQLDatabaseConnector")
    return connector


def _service_factory(service_type: type[ServiceT], connector: Type[SQLDatabaseConnector]) -> ServiceT:
    """Instantiate a model service with the shared connector."""
    return service_type.model_validate({"connector": connector})


def get_users_service(connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)]) -> UsersService:
    """UsersService factory for auth and tenant resolution."""
    return _service_factory(UsersService, connector)


def get_accounts_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> AccountsService:
    """AccountsService factory."""
    return _service_factory(AccountsService, connector)


def get_categories_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> CategoriesService:
    """CategoriesService factory."""
    return _service_factory(CategoriesService, connector)


def get_transactions_service(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> TransactionsService:
    """TransactionsService factory."""
    return _service_factory(TransactionsService, connector)


def get_report_service(connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)]) -> ReportService:
    """ReportService factory."""
    return _service_factory(ReportService, connector)
