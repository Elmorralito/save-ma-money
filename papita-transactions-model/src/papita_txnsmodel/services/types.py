import logging
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.access.types.repository import TypesRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService

logger = logging.getLogger(__name__)


class TypesService(BaseService):

    dto_type: type[TypesDTO] = TypesDTO
    repository_type: type[TypesRepository] = TypesRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
