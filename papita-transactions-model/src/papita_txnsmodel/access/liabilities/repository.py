from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.liabilities.dto import LiabilityAccountsDTO, _ExtendedLiabilityAccountsDTO
from papita_txnsmodel.utils.classutils import MetaSingleton


class LiabilityAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto_type__ = LiabilityAccountsDTO


class ExtendedLiabilityAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto_type__ = _ExtendedLiabilityAccountsDTO
