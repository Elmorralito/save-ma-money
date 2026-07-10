"""HTTP router package for the Papita Transactions API.

Exposes the versioned API surface via :data:`api_v1_router`, which is mounted on the
FastAPI application factory. Routers translate HTTP requests into calls on
``papita_txnsmodel`` services; tenant scoping is enforced in route dependencies
(``get_current_owner``) and passed through to service methods as ``owner=``.

Subpackages:
    v1: Version 1 REST routes (accounts, auth, categories, budgets, health).
"""

from papita_txnsapi.routers.v1 import api_v1_router

__all__ = ["api_v1_router"]
