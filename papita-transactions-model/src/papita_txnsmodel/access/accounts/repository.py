from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton


class AccountsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto_type__ = AccountsDTO
