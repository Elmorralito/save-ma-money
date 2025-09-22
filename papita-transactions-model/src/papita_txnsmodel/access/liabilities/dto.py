import uuid
from typing import Annotated

from pydantic import Field, field_validator, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.types.dto import (
    TypesDTO,
)
from papita_txnsmodel.model.liabilities import (
    BankCreditLiabilityAccounts,
    CreditCardLiabilityAccounts,
    LiabilityAccounts,
)
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class LiabilityAccountsDTO(TableDTO):
    """DTO for LiabilityAccounts model."""

    __dao_type__ = LiabilityAccounts

    account: Annotated[uuid.UUID | AccountsDTO, Field(alias="account_id")]
    account_type: Annotated[uuid.UUID | TypesDTO, Field(alias="account_type_id")]
    months_per_period: int = 1
    initial_value: float
    present_value: float
    monthly_interest_rate: float
    yearly_interest_rate: float
    payment: float
    total_paid: float = 0
    overall_periods: int = 1
    periods_paid: int = 1
    closing_day: int

    @field_validator("months_per_period")
    @classmethod
    def months_per_period_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("months_per_period must be greater than 0")
        return v

    @field_validator("initial_value", "present_value", "payment", "total_paid")
    @classmethod
    def value_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value must be greater than 0")
        return v

    @field_validator("monthly_interest_rate", "yearly_interest_rate")
    @classmethod
    def interest_rate_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("interest rate must be greater than 0")
        return v

    @field_validator("overall_periods", "periods_paid")
    @classmethod
    def periods_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("periods must be greater than 0")
        return v

    @field_validator("closing_day")
    @classmethod
    def closing_day_must_be_valid(cls, v: int) -> int:
        if v <= 0 or v > 28:
            raise ValueError("closing_day must be between 1 and 28")
        return v

    @model_serializer()
    def _serialize(self) -> dict:
        first = convert_dto_obj_on_serialize(
            obj=self,
            id_field="account",
            id_field_attr_name="id",
            target_field="account_id",
            expected_intput_field_type=AccountsDTO,
            expected_output_field_type=uuid.UUID,
        )
        second = convert_dto_obj_on_serialize(
            obj=self,
            id_field="account_type",
            id_field_attr_name="id",
            target_field="account_type_id",
            expected_intput_field_type=TypesDTO,
            expected_output_field_type=uuid.UUID,
        )
        return first | second


class _ExtendedLiabilityAccountsDTO(TableDTO):
    """Base class for extended liability account DTOs."""

    liability_account: Annotated[uuid.UUID | LiabilityAccountsDTO, Field(alias="liability_account_id")]

    @model_serializer()
    def _serialize(self) -> dict:
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="liability_account",
            id_field_attr_name="id",
            target_field="liability_account_id",
            expected_intput_field_type=LiabilityAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )


class BankCreditLiabilityAccountsDTO(_ExtendedLiabilityAccountsDTO):
    """DTO for BankCreditLiabilityAccounts model."""

    __dao_type__ = BankCreditLiabilityAccounts

    insurance_payment: float
    extras_payment: float

    @field_validator("insurance_payment", "extras_payment")
    @classmethod
    def payment_must_be_valid(cls, v: float) -> float:
        if v < 0:
            raise ValueError("payment cannot be negative")
        return v


class CreditCardLiabilityAccountsDTO(_ExtendedLiabilityAccountsDTO):
    """DTO for CreditCardLiabilityAccounts model."""

    __dao_type__ = CreditCardLiabilityAccounts

    credit_limit: float

    @field_validator("credit_limit")
    @classmethod
    def credit_limit_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("credit_limit must be greater than 0")
        return v
