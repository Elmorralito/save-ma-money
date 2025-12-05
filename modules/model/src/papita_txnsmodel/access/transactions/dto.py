"""Transactions DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for transaction entities in the system.
It provides validation and data structures for different types of transactions, including
identified transactions (recurring or planned transactions) and regular transactions.
These DTOs ensure data integrity when transferring transaction data between different
layers of the application.

Classes:
    IdentifiedTransactionsDTO: DTO for planned or recurring transactions.
    TransactionsDTO: DTO for actual financial transactions.
"""

import datetime
import uuid

from pydantic import Field, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import CoreTableDTO, TableDTO
from papita_txnsmodel.model.transactions import IdentifiedTransactions, Transactions
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class IdentifiedTransactionsDTO(CoreTableDTO):
    """DTO for planned or recurring transactions in the system.

    This class represents identified transactions, which are planned or recurring
    financial events that may generate actual transactions. It extends CoreTableDTO to
    inherit common functionality and links to the IdentifiedTransactions ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        name (str): Name of the identified transaction. Must not be empty.
        tags (List[str]): List of tags associated with the transaction. Must contain
            at least one unique item.
        description (str): Description of the transaction. Must not be empty.
        active (bool): Whether the identified transaction is active. Defaults to True.
        planned_value (float): Expected value of the transaction. Must be positive.
        planned_transaction_day (int): Day of the month when the transaction is expected
            to occur. Must be between 1 and 28.
    """

    __dao_type__ = IdentifiedTransactions

    planned_value: float = Field(gt=0, description="Expected value of the transaction")
    planned_transaction_day: int = Field(
        gt=0, le=28, description="Day of the month when the transaction is expected to occur"
    )


class TransactionsDTO(TableDTO):
    """DTO for actual financial transactions in the system.

    This class represents actual financial transactions that have occurred or will occur
    in the system. It extends TableDTO to inherit common functionality and links to the
    Transactions ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        identified_transaction (Optional[uuid.UUID | IdentifiedTransactionsDTO]):
            The identified transaction this transaction is associated with, if any.
        from_account (Optional[uuid.UUID | AccountsDTO]): The source account for the
            transaction, if applicable.
        to_account (Optional[uuid.UUID | AccountsDTO]): The destination account for the
            transaction, if applicable.
        active (bool): Whether the transaction is active. Defaults to True.
        transaction_ts (datetime.datetime): Timestamp when the transaction occurred.
            Defaults to current time.
        value (float): Monetary value of the transaction. Must be positive.
    """

    __dao_type__ = Transactions

    identified_transaction: uuid.UUID | IdentifiedTransactionsDTO | None = Field(
        default=None, serialization_alias="identified_transaction_id"
    )
    from_account: uuid.UUID | AccountsDTO | None = Field(default=None, serialization_alias="from_account_id")
    to_account: uuid.UUID | AccountsDTO | None = Field(default=None, serialization_alias="to_account_id")
    active: bool = True
    transaction_ts: datetime.datetime = Field(default_factory=datetime.datetime.now)
    value: float = Field(gt=0, description="Monetary value of the transaction")

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts nested DTO objects to their ID values for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
        result: dict[str, type] = {}

        if isinstance(self.identified_transaction, IdentifiedTransactionsDTO):
            result |= convert_dto_obj_on_serialize(
                obj=self,
                id_field="identified_transaction",
                id_field_attr_name="id",
                target_field="identified_transaction_id",
                expected_intput_field_type=IdentifiedTransactionsDTO,
                expected_output_field_type=uuid.UUID,
            )

        if isinstance(self.from_account, AccountsDTO):
            result |= convert_dto_obj_on_serialize(
                obj=self,
                id_field="from_account",
                id_field_attr_name="id",
                target_field="from_account_id",
                expected_intput_field_type=AccountsDTO,
                expected_output_field_type=uuid.UUID,
            )

        if isinstance(self.to_account, AccountsDTO):
            result |= convert_dto_obj_on_serialize(
                obj=self,
                id_field="to_account",
                id_field_attr_name="id",
                target_field="to_account_id",
                expected_intput_field_type=AccountsDTO,
                expected_output_field_type=uuid.UUID,
            )

        return result
