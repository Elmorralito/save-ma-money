"""Transactions service module for the Papita Transactions system.

This module provides services for managing transaction entities in the system, including
identified transactions (categorized transactions) and regular transactions. It implements
the necessary functionality to handle the relationships between transactions and other
entities like accounts and categories.

Classes:
    IdentifiedTransactionsService: Service for managing categorized transaction entities.
    TransactionsService: Service for managing transaction entities with links to accounts.
"""

from typing import Annotated, Dict

from pydantic import Field

from papita_txnsmodel.access.transactions.dto import IdentifiedTransactionsDTO, TransactionsDTO
from papita_txnsmodel.access.transactions.repository import IdentifiedTransactionsRepository, TransactionsRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.extends import LinkedEntitiesService, LinkedEntity, TypedEntitiesService


class IdentifiedTransactionsService(TypedEntitiesService):
    """Service for managing categorized transaction entities in the Papita Transactions system.

    This service extends the TypedEntitiesService to handle transactions that have
    category associations. It provides functionality to automatically handle category
    relationships when creating, retrieving, or querying transactions.

    Attributes:
        type_id_column_name (str): Name of the column storing the category ID.
            Set to "category_id".
        type_id_field_name (str): Name of the field storing the category.
            Set to "category".
        dto_type (type[IdentifiedTransactionsDTO]): DTO type for identified transactions.
            Set to IdentifiedTransactionsDTO.
        repository_type (type[IdentifiedTransactionsRepository]): Repository for identified
            transaction database operations. Set to IdentifiedTransactionsRepository.
        types_dto_type (type[TypesDTO]): DTO type for types. Set to TypesDTO.
    """

    type_id_column_name: str = "category_id"
    type_id_field_name: str = "category"
    dto_type: type[IdentifiedTransactionsDTO] = IdentifiedTransactionsDTO
    repository_type: type[IdentifiedTransactionsRepository] = IdentifiedTransactionsRepository
    types_dto_type: type[TypesDTO] = TypesDTO


class TransactionsService(LinkedEntitiesService):
    """Service for managing transaction entities in the Papita Transactions system.

    This service extends the LinkedEntitiesService to handle transactions that have
    relationships with other entities like identified transactions and accounts.
    It provides functionality to automatically handle these relationships when
    creating or retrieving transactions.

    Attributes:
        __links__ (Dict[str, LinkedEntity]): Dictionary defining the relationships
            between transactions and other entities.
        dto_type (type[TransactionsDTO]): DTO type for transactions.
            Set to TransactionsDTO.
        repository_type (type[TransactionsRepository]): Repository for transaction
            database operations. Set to TransactionsRepository.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
            Set to 0.0, meaning no tolerance for missing upsertions.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Set to OnUpsertConflictDo.UPDATE to update existing records.
    """

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
