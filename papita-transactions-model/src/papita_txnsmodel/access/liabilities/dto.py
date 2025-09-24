"""Liabilities DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for liability entities in the system.
It provides validation and data structures for different types of liabilities, including
general liabilities, bank credit liabilities, and credit card liabilities. These DTOs
ensure data integrity when transferring liability data between different layers of the
application.

Classes:
    LiabilityAccountsDTO: Base DTO for all liability accounts.
    ExtendedLiabilityAccountsDTO: Base DTO for specialized liability accounts.
    BankCreditLiabilityAccountsDTO: DTO for bank credit liability accounts.
    CreditCardLiabilityAccountsDTO: DTO for credit card liability accounts.
"""

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
    """DTO for liability accounts with financial attributes and relationships.

    This class represents liability accounts in the system and includes validation
    rules to ensure data integrity. It extends TableDTO to inherit common
    functionality and links to the LiabilityAccounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        account (uuid.UUID | AccountsDTO): The account associated with this liability.
        account_type (uuid.UUID | TypesDTO): The type of this liability account.
        months_per_period (int): Number of months in each accounting period. Defaults to 1.
        initial_value (float): Initial value of the liability. Must be positive.
        present_value (float): Current value of the liability. Must be positive.
        monthly_interest_rate (float): Monthly interest rate. Must be positive.
        yearly_interest_rate (float): Yearly interest rate. Must be positive.
        payment (float): Regular payment amount. Must be positive.
        total_paid (float): Total amount paid so far. Defaults to 0.
        overall_periods (int): Total number of payment periods. Defaults to 1.
        periods_paid (int): Number of periods already paid. Defaults to 1.
        closing_day (int): Day of the month when the payment is due (1-28).
    """

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
        """Validate that months_per_period is positive.

        Args:
            v: The months_per_period value to validate.
        Returns:
            int: The validated months_per_period.

        Raises:
            ValueError: If months_per_period is not greater than 0.
        """
        if v <= 0:
            raise ValueError("months_per_period must be greater than 0")
        return v

    @field_validator("initial_value", "present_value", "payment", "total_paid")
    @classmethod
    def value_must_be_positive(cls, v: float) -> float:
        """Validate that financial values are positive.

        Args:
            v: The financial value to validate.
        Returns:
            float: The validated financial value.

        Raises:
            ValueError: If the value is not greater than 0.
        """
        if v <= 0:
            raise ValueError("value must be greater than 0")
        return v

    @field_validator("monthly_interest_rate", "yearly_interest_rate")
    @classmethod
    def interest_rate_must_be_positive(cls, v: float) -> float:
        """Validate that interest rates are positive.

        Args:
            v: The interest rate value to validate.
        Returns:
            float: The validated interest rate.

        Raises:
            ValueError: If the interest rate is not greater than 0.
        """
        if v <= 0:
            raise ValueError("interest rate must be greater than 0")
        return v

    @field_validator("overall_periods", "periods_paid")
    @classmethod
    def periods_must_be_positive(cls, v: int) -> int:
        """Validate that period counts are positive.

        Args:
            v: The period count to validate.

        Returns:
            int: The validated period count.

        Raises:
            ValueError: If the period count is not greater than 0.
        """
        if v <= 0:
            raise ValueError("periods must be greater than 0")
        return v

    @field_validator("closing_day")
    @classmethod
    def closing_day_must_be_valid(cls, v: int) -> int:
        """Validate that closing_day is within valid range.

        Args:
            v: The closing_day value to validate.

        Returns:
            int: The validated closing_day.

        Raises:
            ValueError: If closing_day is not between 1 and 28.
        """
        if v <= 0 or v > 28:
            raise ValueError("closing_day must be between 1 and 28")
        return v

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts nested DTO objects to their ID values for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
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


class ExtendedLiabilityAccountsDTO(TableDTO):
    """Base DTO for specialized liability account types.

    This class serves as a base for more specific liability account DTOs, providing
    a common structure for linking to the base liability account.

    Attributes:
        liability_account (uuid.UUID | LiabilityAccountsDTO): The base liability account
            associated with this specialized liability account.
    """

    liability_account: Annotated[uuid.UUID | LiabilityAccountsDTO, Field(alias="liability_account_id")]

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts the nested liability_account DTO to its ID value for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="liability_account",
            id_field_attr_name="id",
            target_field="liability_account_id",
            expected_intput_field_type=LiabilityAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )


class BankCreditLiabilityAccountsDTO(ExtendedLiabilityAccountsDTO):
    """DTO for bank credit liability accounts.

    This class represents bank credit liability accounts in the system, such as
    mortgages, personal loans, and auto loans. It extends ExtendedLiabilityAccountsDTO
    to inherit the liability account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        insurance_payment (float): Additional payment for insurance. Cannot be negative.
        extras_payment (float): Additional miscellaneous payments. Cannot be negative.
    """

    __dao_type__ = BankCreditLiabilityAccounts

    insurance_payment: float
    extras_payment: float

    @field_validator("insurance_payment", "extras_payment")
    @classmethod
    def payment_must_be_valid(cls, v: float) -> float:
        """Validate that additional payments are not negative.

        Args:
            v: The payment value to validate.

        Returns:
            float: The validated payment value.

        Raises:
            ValueError: If the payment is negative.
        """
        if v < 0:
            raise ValueError("payment cannot be negative")
        return v


class CreditCardLiabilityAccountsDTO(ExtendedLiabilityAccountsDTO):
    """DTO for credit card liability accounts.

    This class represents credit card liability accounts in the system. It extends
    ExtendedLiabilityAccountsDTO to inherit the liability account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        credit_limit (float): Maximum credit limit. Must be positive.
    """

    __dao_type__ = CreditCardLiabilityAccounts

    credit_limit: float

    @field_validator("credit_limit")
    @classmethod
    def credit_limit_must_be_positive(cls, v: float) -> float:
        """Validate that credit_limit is positive.

        Args:
            v: The credit_limit value to validate.

        Returns:
            float: The validated credit_limit.

        Raises:
            ValueError: If credit_limit is not greater than 0.
        """
        if v <= 0:
            raise ValueError("credit_limit must be greater than 0")
        return v
