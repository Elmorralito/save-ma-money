"""Types repository module for the Papita Transactions system.

This module defines repository classes for type entities in the system.
It provides database access operations specific to types, extending the base
repository functionality with type-specific implementations.

Classes:
    TypesRepository: Repository for general type entity database operations.
    TypesClassificationRepository: Repository for type classification operations.
"""

from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import TypesClassificationsDTO, TypesDTO


class TypesClassificationRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for type classification database operations.

    This class extends the BaseRepository to provide operations specific to type
    classifications in the system. Type classifications organize and categorize the
    different types of financial entities. It uses the Singleton pattern via
    MetaSingleton to ensure only one instance exists throughout the application.

    The repository works with TypesClassificationsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting, updating,
    and deleting type classification records.

    Attributes:
        __expected_dto_type__ (type[TypesClassificationsDTO]): The expected DTO type for this
            repository, set to TypesClassificationsDTO.
    """

    __expected_dto_type__ = TypesClassificationsDTO


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
