"""Papita Transactions model services.

Services provide the business logic layer and work with the owner column via
UsersDTO. Use UsersService.get_owner(owner_id) to resolve an owner id to a
UsersDTO for passing as owner= to other services and handlers.
"""

from papita_txnsmodel.services.users import UsersService

__all__ = ["UsersService"]
