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
from typing import Annotated, List, Optional

from pydantic import Field, field_validator, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.model.transactions import IdentifiedTransactions, Transactions
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class IdentifiedTransactionsDTO(TableDTO):
    """DTO for planned or recurring transactions in the system.

    This class represents identified transactions, which are planned or recurring
    financial events that may generate actual transactions. It extends TableDTO to
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

    name: str
    tags: List[str]
    description: str
    active: bool = True
    planned_value: float
    planned_transaction_day: int

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that the name is not empty.

        Args:
            v: The name value to validate.
        Returns:
            str: The validated name.

        Raises:
            ValueError: If the name is empty or contains only whitespace.
        """
        if not v or v.isspace():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        """Validate that the description is not empty.

        Args:
            v: The description value to validate.

        Returns:
            str: The validated description.

        Raises:
            ValueError: If the description is empty or contains only whitespace.
        """
        if not v or v.isspace():
            raise ValueError("description cannot be empty")
        return v

    @field_validator("tags")
    @classmethod
    def tags_must_have_at_least_one_item(cls, v: List[str]) -> List[str]:
        """Validate that the tags list has at least one item and contains unique items.

        Args:
            v: The tags list to validate.
        Returns:
            List[str]: The validated tags list.

        Raises:
            ValueError: If the tags list is empty or contains duplicate items.
        """
        if not v or len(v) < 1:
            raise ValueError("tags must have at least one item")

        # Check for unique items
        if len(v) != len(set(v)):
            raise ValueError("tags must contain unique items")
        return v

    @field_validator("planned_value")
    @classmethod
    def planned_value_must_be_positive(cls, v: float) -> float:
        """Validate that planned_value is positive.

        Args:
            v: The planned_value to validate.
        Returns:
            float: The validated planned_value.

        Raises:
            ValueError: If planned_value is not greater than 0.
        """
        if v <= 0:
            raise ValueError("planned_value must be greater than 0")
        return v

    @field_validator("planned_transaction_day")
    @classmethod
    def planned_transaction_day_must_be_valid(cls, v: int) -> int:
        """Validate that planned_transaction_day is within valid range.

        Args:
            v: The planned_transaction_day value to validate.

        Returns:
            int: The validated planned_transaction_day.

        Raises:
            ValueError: If planned_transaction_day is not between 1 and 28.
        """
        if v <= 0:
            raise ValueError("planned_transaction_day must be greater than 0")
        if v > 28:
            raise ValueError("planned_transaction_day must be less than or equal to 28")
        return v


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

    identified_transaction: Optional[
        Annotated[uuid.UUID | IdentifiedTransactionsDTO, Field(alias="identified_transaction_id")]
    ] = None
    from_account: Optional[Annotated[uuid.UUID | AccountsDTO, Field(alias="from_account_id")]] = None
    to_account: Optional[Annotated[uuid.UUID | AccountsDTO, Field(alias="to_account_id")]] = None
    active: bool = True
    transaction_ts: datetime.datetime = Field(default_factory=datetime.datetime.now)
    value: float

    @field_validator("value")
    @classmethod
    def value_must_be_positive(cls, v: float) -> float:
        """Validate that value is positive.

        Args:
            v: The transaction value to validate.

        Returns:
            float: The validated transaction value.

        Raises:
            ValueError: If value is not greater than 0.
        """
        if v <= 0:
            raise ValueError("value must be greater than 0")
        return v

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
