import datetime
import uuid
from typing import Annotated, List, Optional

from pydantic import Field, field_validator, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.model.transactions import IdentifiedTransactions, Transactions
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class IdentifiedTransactionsDTO(TableDTO):
    """DTO for IdentifiedTransactions model."""

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
        if not v or v.isspace():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError("description cannot be empty")
        return v

    @field_validator("tags")
    @classmethod
    def tags_must_have_at_least_one_item(cls, v: List[str]) -> List[str]:
        if not v or len(v) < 1:
            raise ValueError("tags must have at least one item")

        # Check for unique items
        if len(v) != len(set(v)):
            raise ValueError("tags must contain unique items")

        return v

    @field_validator("planned_value")
    @classmethod
    def planned_value_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("planned_value must be greater than 0")
        return v

    @field_validator("planned_transaction_day")
    @classmethod
    def planned_transaction_day_must_be_valid(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("planned_transaction_day must be greater than 0")
        if v > 28:
            raise ValueError("planned_transaction_day must be less than or equal to 28")
        return v


class TransactionsDTO(TableDTO):
    """DTO for Transactions model."""

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
        if v <= 0:
            raise ValueError("value must be greater than 0")
        return v

    @model_serializer()
    def _serialize(self) -> dict:
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
