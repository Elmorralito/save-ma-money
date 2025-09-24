"""Types repository module for the Papita Transactions system.

This module defines the repository class for type entities in the system.
It provides database access operations specific to types, extending the base
repository functionality with type-specific implementations.

Classes:
    TypesRepository: Repository for type entity database operations.
"""

from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.utils.classutils import MetaSingleton


class TypesRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for type entity database operations.

    This class extends the BaseRepository to provide operations specific to type
    entities, which categorize different financial objects in the system such as
    assets, liabilities, and transactions. It uses the Singleton pattern via
    MetaSingleton to ensure only one instance exists throughout the application.

    The repository works with TypesDTO objects and provides all the CRUD operations
    inherited from BaseRepository, including querying, inserting, updating, and
    deleting type records.

    Attributes:
        __expected_dto_type__ (type[TypesDTO]): The expected DTO type for this
            repository, set to TypesDTO.
    """

    __expected_dto_type__ = TypesDTO
