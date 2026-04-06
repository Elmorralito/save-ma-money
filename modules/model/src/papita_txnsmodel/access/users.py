"""Users repository module for the Papita Transactions system.

This module provides the implementation of the UsersRepository, which handles
database operations specifically for user entities.
"""

from papita_txnsmodel.model.users import Users
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import BaseRepository


class UsersRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository class for managing user entities in the database.

    This class extends BaseRepository to provide specialized operations for
    user-related data. It uses the singleton pattern to ensure a single
    repository instance is used throughout the application.

    Attributes:
        __expected_dao_type__ (type[Users]): The DAO class associated with this
            repository, set to Users.
    """

    __expected_dao_type__ = Users
