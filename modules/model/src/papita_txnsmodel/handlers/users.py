# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""Users table handler for tenant root ingest."""

from typing import Tuple

from papita_txnsmodel.services.users import UsersService

from .base import BaseTableHandler


class UsersTableHandler(BaseTableHandler[UsersService, ...]):
    """Handler for loading and processing user table data.

    Users are the tenant root; this handler supports registrar/bootstrap ingest
    of user rows before owned-table loads that require ``owner=UsersDTO``.
    """

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this handler."""
        return "users", "users_table", "user_table"
