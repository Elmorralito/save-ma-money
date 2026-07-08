"""Transactions repository module for the Papita Transactions system.

This module defines the repository classes for transaction entities in the system.
It provides database access operations specific to transactions, extending the base
repository functionality with transaction-specific implementations.

Classes:
    TransactionTemplatesRepository: Repository for planned or recurring template operations.
    TransactionsRepository: Repository for posted financial transaction operations.
"""

from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import TransactionsDTO, TransactionTemplatesDTO


class TransactionTemplatesRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for transaction template database operations.

    This class extends OwnedTableRepository to provide operations specific to
    transaction templates. It uses the Singleton pattern via MetaSingleton to ensure
    only one instance exists throughout the application.

    Attributes:
        __expected_dto__ (type[TransactionTemplatesDTO]): The expected DTO type for this
            repository, set to TransactionTemplatesDTO.
    """

    __expected_dto__ = TransactionTemplatesDTO


class TransactionsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for posted financial transaction database operations.

    This class extends OwnedTableRepository to provide operations specific to posted
    transactions. It uses the Singleton pattern via MetaSingleton to ensure only one
    instance exists throughout the application.

    Attributes:
        __expected_dto__ (type[TransactionsDTO]): The expected DTO type for this
            repository, set to TransactionsDTO.
    """

    __expected_dto__ = TransactionsDTO
