from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.transactions.dto import IdentifiedTransactionsDTO, TransactionsDTO
from papita_txnsmodel.utils.classutils import MetaSingleton


class IdentifiedTransactionsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto__ = IdentifiedTransactionsDTO


class TransactionsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto__ = TransactionsDTO
