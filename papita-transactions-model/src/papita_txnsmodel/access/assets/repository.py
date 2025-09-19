from papita_txnsmodel.access.assets.dto import AssetAccountsDTO, ExtendedAssetAccountDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton


class AssetAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto__ = AssetAccountsDTO


class ExtendedAssetAccountRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto__ = ExtendedAssetAccountDTO
