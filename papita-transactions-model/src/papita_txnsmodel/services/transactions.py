from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.transactions.dto import IdentifiedTransactionsDTO, TransactionsDTO
from papita_txnsmodel.access.transactions.repository import IdentifiedTransactionsRepository, TransactionsRepository
from papita_txnsmodel.access.types.dto import TransactionCategoriesDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.extends import TypedEntitiesService


class IdentifiedTransactionsService(TypedEntitiesService):

    type_id_column_name: str = "category_id"
    type_id_field_name: str = "category"
    dto_type: type[IdentifiedTransactionsDTO] = IdentifiedTransactionsDTO
    repository_type: type[IdentifiedTransactionsRepository] = IdentifiedTransactionsRepository
    types_dto_type: type[TransactionCategoriesDTO] = TransactionCategoriesDTO


class TransactionsService(BaseService):

    dto_type: type[TransactionsDTO] = TransactionsDTO
    repository_type: type[TransactionsRepository] = TransactionsRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
