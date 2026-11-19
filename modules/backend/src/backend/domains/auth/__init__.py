"""Auth & Users vertical slice (models, schemas, service, router)."""

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.routers.v1.auth import router
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.model.users import Users
from papita_txnsmodel.services.users import UsersService

__all__ = [
    "Users",
    "UsersDTO",
    "UsersRepository",
    "UsersService",
    "get_current_owner",
    "router",
]
