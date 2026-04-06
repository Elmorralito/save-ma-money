from papita_txnsmodel.model.markets import MarketAssetGroups, MarketAssets
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import BaseRepository


class MarketAssetGroupsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for market asset group database operations.

    This class extends the BaseRepository to provide market asset group-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.
    """

    __expected_dao_type__ = MarketAssetGroups


class MarketAssetsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for market asset database operations.

    This class extends the BaseRepository to provide market asset-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.
    """

    __expected_dao_type__ = MarketAssets
