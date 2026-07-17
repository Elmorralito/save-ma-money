"""FastAPI dependency injection surface for the Papita Transactions API.

Re-exports auth, pagination, service factory, tenant-context, and Redis
dependencies used by route handlers. Import from this package rather than
individual ``dependencies.*`` modules to keep router wiring consistent.

Exported symbols:
    Auth: ``get_auth_manager``, ``get_current_owner``, ``oauth2_scheme``
    Pagination: ``PaginationParams``, ``get_pagination``
    Redis: ``get_optional_redis``, ``get_session_store``
    Services: ``get_accounts_service``, ``get_categories_service``,
        ``get_connector``, ``get_report_service``, ``get_transactions_service``,
        ``get_users_service``
    Tenancy: ``TenantContext``
"""

from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner, oauth2_scheme
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import (
    get_accounts_service,
    get_categories_service,
    get_connector,
    get_report_service,
    get_transactions_service,
    get_users_service,
)
from papita_txnsapi.dependencies.session_store import get_session_store
from papita_txnsapi.dependencies.tenant import TenantContext

__all__ = [
    "PaginationParams",
    "TenantContext",
    "get_accounts_service",
    "get_auth_manager",
    "get_categories_service",
    "get_connector",
    "get_current_owner",
    "get_optional_redis",
    "get_pagination",
    "get_report_service",
    "get_session_store",
    "get_transactions_service",
    "get_users_service",
    "oauth2_scheme",
]
