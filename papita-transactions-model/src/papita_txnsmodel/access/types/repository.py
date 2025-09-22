from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.utils.classutils import MetaSingleton


class TypesRepository(BaseRepository, metaclass=MetaSingleton):
    __expected_dto_type__ = TypesDTO
