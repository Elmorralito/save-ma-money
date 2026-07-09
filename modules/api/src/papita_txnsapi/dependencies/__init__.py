"""FastAPI dependencies."""

from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner, oauth2_scheme
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.services import (
    get_accounts_service,
    get_categories_service,
    get_connector,
    get_report_service,
    get_transactions_service,
    get_users_service,
)
from papita_txnsapi.dependencies.tenant import TenantContext

__all__ = [
    "PaginationParams",
    "TenantContext",
    "get_accounts_service",
    "get_auth_manager",
    "get_categories_service",
    "get_connector",
    "get_current_owner",
    "get_pagination",
    "get_report_service",
    "get_transactions_service",
    "get_users_service",
    "oauth2_scheme",
]
