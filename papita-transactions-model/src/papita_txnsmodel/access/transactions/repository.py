"""Transactions repository module for the Papita Transactions system.

This module defines the repository classes for transaction entities in the system.
It provides database access operations specific to transactions, extending the base
repository functionality with transaction-specific implementations.

Classes:
    IdentifiedTransactionsRepository: Repository for planned or recurring transaction operations.
    TransactionsRepository: Repository for actual financial transaction operations.
"""

from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.transactions.dto import IdentifiedTransactionsDTO, TransactionsDTO
from papita_txnsmodel.utils.classutils import MetaSingleton


class IdentifiedTransactionsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for planned or recurring transaction database operations.

    This class extends the BaseRepository to provide operations specific to identified
    (planned or recurring) transactions. It uses the Singleton pattern via MetaSingleton
    to ensure only one instance exists throughout the application.

    The repository works with IdentifiedTransactionsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting, updating,
    and deleting identified transaction records.

    Attributes:
        __expected_dto__ (type[IdentifiedTransactionsDTO]): The expected DTO type for this
            repository, set to IdentifiedTransactionsDTO.
    """

    __expected_dto__ = IdentifiedTransactionsDTO


class TransactionsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for actual financial transaction database operations.

    This class extends the BaseRepository to provide operations specific to actual
    financial transactions. It uses the Singleton pattern via MetaSingleton to ensure
    only one instance exists throughout the application.

    The repository works with TransactionsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting, updating,
    and deleting transaction records.

    Attributes:
        __expected_dto__ (type[TransactionsDTO]): The expected DTO type for this
            repository, set to TransactionsDTO.
    """

    __expected_dto__ = TransactionsDTO
