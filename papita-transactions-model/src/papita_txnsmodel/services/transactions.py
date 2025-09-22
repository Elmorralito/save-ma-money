from typing import Annotated, Dict

from pydantic import Field

from papita_txnsmodel.access.transactions.dto import IdentifiedTransactionsDTO, TransactionsDTO
from papita_txnsmodel.access.transactions.repository import IdentifiedTransactionsRepository, TransactionsRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.extends import LinkedEntitiesService, LinkedEntity, TypedEntitiesService


class IdentifiedTransactionsService(TypedEntitiesService):

    type_id_column_name: str = "category_id"
    type_id_field_name: str = "category"
    dto_type: type[IdentifiedTransactionsDTO] = IdentifiedTransactionsDTO
    repository_type: type[IdentifiedTransactionsRepository] = IdentifiedTransactionsRepository
    types_dto_type: type[TypesDTO] = TypesDTO


class TransactionsService(LinkedEntitiesService):

    __links__: Dict[str, LinkedEntity] = {
        "asset_accidentified_transactionount": LinkedEntity(
            expected_other_entity_service_type=IdentifiedTransactionsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="identified_transaction_id",
            own_entity_link_field_name="identified_transaction",
        ),
        "from_account": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="from_account_id",
            own_entity_link_field_name="from_account",
        ),
        "to_account": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="to_account_id",
            own_entity_link_field_name="to_account",
        ),
    }

    dto_type: type[TransactionsDTO] = TransactionsDTO
    repository_type: type[TransactionsRepository] = TransactionsRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
